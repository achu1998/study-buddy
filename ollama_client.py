# LLM Client supporting local Ollama and Anthropic Claude
# Automatically switches based on config.py settings

import httpx
import json
import re
import os
from typing import List, Dict, Tuple
from anthropic import Anthropic
from google import genai
from config import DEPLOYMENT_MODE, LLM_PROVIDER

if DEPLOYMENT_MODE == "local":
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
else:
    OLLAMA_BASE_URL = None
    OLLAMA_MODEL = None
    from config import API_KEY, MODEL_NAME

from prompts import (
    STUDY_BUDDY_SYSTEM_PROMPT,
    get_tier_selection_prompt,
    get_summarization_prompt,
    get_mcq_generation_prompt
)

class OllamaClient:
    """Client for interacting with local Ollama or Anthropic Claude models"""
    
    def __init__(self):
        """
        Initialize LLM client based on config.py settings
        Automatically detects deployment mode and uses appropriate provider
        """
        # Import config here to avoid circular imports
        
        self.deployment_mode = DEPLOYMENT_MODE
        self.timeout = 600.0  # 10 minutes for longer responses
        self.provider = LLM_PROVIDER
        
        if self.deployment_mode == "cloud":
            # Cloud deployment - use Anthropic
            self.api_key = API_KEY
            
            if not self.api_key:
                raise ValueError("API_KEY is required for cloud deployment. Check your .env file.")
            
            # Import Anthropic client
            try:
                if self.provider == "anthropic":
                    self.anthropic_client = Anthropic(api_key=self.api_key)
                if self.provider == "gemini":
                    self.gemini_client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not found. Run: pip install anthropic")
            
            self.model = MODEL_NAME
                
            print(f"🌐 Using model: {self.model}")
            
        else:
            # Local deployment - use Ollama
            self.base_url = OLLAMA_BASE_URL
            self.model = OLLAMA_MODEL
            
            print(f"💻 Using local Ollama: {self.model}")
    
    def _make_request(self, prompt: str, system: str, temperature: float = 0.3, 
                     max_tokens: int = 500) -> str:
        """Make request to either Ollama or Anthropic based on deployment mode"""
        
        if self.provider == "ollama":
            return self._make_ollama_request(prompt, system, temperature, max_tokens)
        elif self.provider == "anthropic":
            return self._make_anthropic_request(prompt, system, temperature, max_tokens)
        else:
            return self._make_gemini_request(prompt, system, temperature, max_tokens)
            
    
    def _make_anthropic_request(self, prompt: str, system: str, temperature: float, 
                               max_tokens: int) -> str:
        """Make request to Anthropic Claude API"""
        
        try:
            message = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract text from response
            return message.content[0].text
            
        except Exception as e:
            raise Exception(f"Error communicating with Anthropic: {str(e)}")
        
    

    def _make_gemini_request(self, prompt: str, system: str, temperature: float,
                        max_tokens: int) -> str:
        """Make request to Google Gemini API using google.genai Client"""
        
        try:
            print("Sending request to Gemini...")
            
            # Combine system instruction with user prompt
            # Gemini's client.models.generate_content expects a single content string
            full_prompt = f"{system}\n\nUser: {prompt}"
            
            # Generate content using the new API
            response = self.gemini_client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )
            
            print("Response received from Gemini!")
            
            # Extract text from response
            return response.text
            
        except Exception as e:
            print(f"Gemini error details: {str(e)}")
            raise Exception(f"Error communicating with Gemini: {str(e)}")


    
    def _make_ollama_request(self, prompt: str, system: str, temperature: float, 
                            max_tokens: int) -> str:
        """Make synchronous request to Ollama API"""
        
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "temperature": temperature,
            "top_p": 0.9,
            "num_predict": max_tokens,
            "stream": False
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except httpx.TimeoutException:
            raise Exception("Request timed out. Please try again.")
        except httpx.ConnectError:
            raise Exception("Cannot connect to Ollama. Please ensure Ollama is running.")
        except Exception as e:
            raise Exception(f"Error communicating with Ollama: {str(e)}")
    
    def classify_tier(self, user_message: str, conversation_history: List[Dict]) -> int:
        """
        Classify which response tier (1-5) is appropriate based on student's query
        
        Tier 1: Clarification - Student shows confusion about terminology
        Tier 2: Scaffolding - Student has partial understanding
        Tier 3: Skeleton Code - Student needs structural guidance
        Tier 4: Process Hints - Student needs methodology guidance
        Tier 5: Resource Pointers - Student needs conceptual orientation
        """
        
        message_lower = user_message.lower()
        
        # Check conversation history for pattern of understanding
        history_length = len(conversation_history)
        
        # Tier 1: Confusion signals
        confusion_keywords = ["what does", "what is", "define", "meaning", "confused", 
                             "don't understand", "unclear", "explain"]
        if any(keyword in message_lower for keyword in confusion_keywords):
            return 1
        
        # Tier 2: Partial understanding - student showing work
        partial_keywords = ["tried", "attempted", "got", "wrong", "here's what", 
                           "this is my", "i think"]
        if any(keyword in message_lower for keyword in partial_keywords):
            return 2
        
        # Tier 3: Structure request
        structure_keywords = ["how do i", "step by step", "structure", "template", 
                             "skeleton", "outline", "format"]
        if any(keyword in message_lower for keyword in structure_keywords):
            return 3
        
        # Tier 4: Methodology request
        method_keywords = ["approach", "method", "algorithm", "strategy", "concept",
                          "which way", "best way"]
        if any(keyword in message_lower for keyword in method_keywords):
            return 4
        
        # Tier 5: Resource pointer (default for vague questions)
        return 5
    
    def generate_chat_response(
        self,
        session_id: str,
        user_message: str,
        conversation_history: List[Dict],
        course_context: str = None
    ) -> Tuple[str, int, List[Dict]]:
        """
        Generate a Socratic response to student's message
        
        Returns:
            (response_text, response_tier, citations)
        """
        
        # Classify tier
        tier = self.classify_tier(user_message, conversation_history)
        
        # Build conversation context (last 6-8 messages for context window)
        context_messages = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
        
        conversation_text = "\n".join([
            f"{'Student' if msg['role'] == 'user' else 'Tutor'}: {msg['content']}"
            for msg in context_messages
        ])
        
        # Build system prompt with tier guidance
        system_prompt = STUDY_BUDDY_SYSTEM_PROMPT + f"\n\n**Current Response Tier: {tier}**\n"
        
        if course_context:
            system_prompt += f"\n**Course Material Context Available**: Use this to provide more relevant guidance.\n"
        
        # Build full prompt
        full_prompt = f"{conversation_text}\nStudent: {user_message}\nTutor:"
        
        # Generate response
        response = self._make_request(
            prompt=full_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=400
        )
        
        # Check if response is a full solution (guardrail)
        if self._is_solution_response(response):
            response = self._reframe_as_guidance(response, tier)
        
        # Ensure response length is appropriate (200-300 words)
        response = self._truncate_to_word_limit(response, max_words=300)
        
        # Extract citations
        citations = self._extract_citations(response)
        
        return response.strip(), tier, citations
    
    def _is_solution_response(self, text: str) -> bool:
        """Check if response contains a complete solution (guardrail check)"""
        
        # Count lines of non-comment code
        lines = text.split('\n')
        code_lines = [
            l for l in lines 
            if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('//')
        ]
        
        # If more than 20 lines of code without TODOs, likely a full solution
        if len(code_lines) > 20 and 'TODO' not in text:
            return True
        
        # Check for complete function definitions
        complete_patterns = [
            r'def\s+\w+\([^)]*\):[\s\S]*return\s+\w+',  # Python function with return
            r'function\s+\w+\([^)]*\)\s*{[\s\S]*return\s+',  # JS function
            r'class\s+\w+:[\s\S]{100,}',  # Long class definition
        ]
        
        for pattern in complete_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _reframe_as_guidance(self, response: str, tier: int) -> str:
        """Reframe a solution-providing response as guidance"""
        
        return f"""I notice I was about to provide too much of a complete solution. Let me reframe this as guidance instead:

        Instead of giving you the full answer, let me help you think through this step by step:

        1. What's the core problem you're trying to solve?
        2. What approaches have you considered?
        3. What's stopping you from moving forward?

        Remember: The goal is for YOU to understand how to solve this, not just to get an answer. Let's work through your thinking process together.

        What specific part would you like to focus on first?"""
    
    def _truncate_to_word_limit(self, text: str, max_words: int = 300) -> str:
        """Ensure response stays within word limit"""
        words = text.split()
        if len(words) > max_words:
            truncated = " ".join(words[:max_words])
            return truncated + "\n\n[Response truncated to stay focused. What specific aspect would you like to explore further?]"
        return text
    
    def _extract_citations(self, response: str) -> List[Dict]:
        """Extract citation references from response text"""
        citations = []
        
        # Look for patterns like [c1], [concept:X], etc.
        patterns = re.findall(r'\[(c\d+|concept:[^\]]+)\]', response, re.IGNORECASE)
        
        for idx, pattern in enumerate(patterns):
            citations.append({
                "id": pattern,
                "type": "concept_reference" if "concept:" in pattern else "citation",
                "concept": pattern.replace("concept:", "").strip()
            })
        
        return citations
    
    def generate_summary(self, course_material: str, max_length: int = 500) -> str:
        """
        Generate a concise summary of course material
        
        Args:
            course_material: Extracted text from PDF
            max_length: Maximum words in summary
        
        Returns:
            Formatted summary with key points
        """
        
        # Truncate material if too long (avoid context overflow)
        words = course_material.split()
        if len(words) > 1500:
            material_excerpt = " ".join(words[:1500]) + "\n[Material truncated for processing...]"
        else:
            material_excerpt = course_material
        
        system_prompt = get_summarization_prompt()
        
        prompt = f"""Course Material:
        {material_excerpt}

        Please provide a comprehensive yet concise summary covering:
        1. Main topics and concepts
        2. Key definitions and terminology
        3. Important principles or theories
        4. Practical applications or examples
        5. Core takeaways

        Format as bullet points for clarity."""
        
        summary = self._make_request(
            prompt=prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=400
        )
        
        return summary.strip()
    
    def generate_mcq(self, course_material: str, num_questions: int = 5) -> List[Dict]:
        """
        Generate multiple choice questions from course material
        
        Args:
            course_material: Extracted text from PDF
            num_questions: Number of questions to generate
        
        Returns:
            List of question dictionaries with format:
            {
                "question": str,
                "options": List[str],
                "correct_answer": str,
                "explanation": str
            }
        """
        
        # Truncate material if too long
        words = course_material.split()
        if len(words) > 3000:
            material_excerpt = " ".join(words[:3000])
        else:
            material_excerpt = course_material
        
        system_prompt = get_mcq_generation_prompt()
        
        prompt = f"""Course Material:
        {material_excerpt}

        Generate {num_questions} multiple choice questions that test understanding of key concepts.

        IMPORTANT RULES:
        - Each question must have EXACTLY 4 options labeled A, B, C, D
        - No more than 4 options per question
        - No additional options beyond D

        For each question, provide:
        1. A clear question
        2. EXACTLY four options (A, B, C, D) - NO MORE
        3. The correct answer (must be A, B, C, or D)
        4. A brief explanation

        Format each question EXACTLY as shown below:
        QUESTION: [question text]
        A) [option A]
        B) [option B]
        C) [option C]
        D) [option D]
        CORRECT: [A/B/C/D]
        EXPLANATION: [explanation]

        ---

        Generate {num_questions} questions now:"""
        
        response = self._make_request(
            prompt=prompt,
            system=system_prompt,
            temperature=0.5,  # Slightly higher for variety
            max_tokens=800
        )
        
        # Parse response into structured format
        questions = self._parse_mcq_response(response)
        
        return questions[:num_questions]  # Ensure we return exactly num_questions
    
    def _parse_mcq_response(self, response: str) -> List[Dict]:
        """Parse MCQ response text into structured format - optimized for actual LLM output"""
        
        questions = []
        
        # Split by question markers - handle both numbered and unnumbered formats
        question_blocks = re.split(r'\*\*Question \d+\*\*|\n\n(?=\*\*Question)', response)
        
        for block in question_blocks:
            if not block.strip() or len(block.strip()) < 20:
                continue
            
            try:
                # Extract question text - look for text before option A
                # Pattern: Everything before "A)" is the question
                question_match = re.search(r'^(.+?)(?=\n\s*A\))', block, re.DOTALL)
                if not question_match:
                    continue
                
                question_text = question_match.group(1).strip()
                # Remove any leading "What is..." formatting artifacts
                question_text = re.sub(r'^\s*\n+', '', question_text)
                
                # Extract options A, B, C, D
                # Pattern: Letter) followed by text until next letter or CORRECT
                options_dict = {}
                for letter in ['A', 'B', 'C', 'D']:
                    pattern = rf'{letter}\)\s*(.+?)(?=\n\s*[A-D]\)|\n\s*CORRECT:|\Z)'
                    opt_match = re.search(pattern, block, re.DOTALL)
                    if opt_match:
                        option_text = opt_match.group(1).strip()
                        # Clean up any extra whitespace or newlines
                        option_text = ' '.join(option_text.split())
                        options_dict[letter] = option_text
                
                # Verify we have exactly 4 options
                if len(options_dict) != 4:
                    continue
                
                # Build options list
                options = [
                    f"A) {options_dict['A']}",
                    f"B) {options_dict['B']}",
                    f"C) {options_dict['C']}",
                    f"D) {options_dict['D']}"
                ]
                
                # Extract correct answer
                correct_match = re.search(r'CORRECT:\s*([A-D])', block)
                if not correct_match:
                    continue
                
                correct_letter = correct_match.group(1).upper()
                correct_answer = f"{correct_letter}) {options_dict[correct_letter]}"
                
                # Extract explanation
                explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?=\*\*Question|\Z)', block, re.DOTALL)
                explanation = "No explanation provided."
                if explanation_match:
                    explanation = explanation_match.group(1).strip()
                    # Clean up extra whitespace
                    explanation = ' '.join(explanation.split())
                
                # Build question object
                questions.append({
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": explanation
                })
                
            except Exception as e:
                # Skip malformed questions but log the error
                print(f"Warning: Failed to parse question block: {str(e)}")
                continue
        
        # If parsing failed completely, return fallback
        if not questions:
            print("WARNING: No questions parsed from LLM response. Using fallback.")
            questions = self._generate_fallback_questions()
        
        return questions
    
    def _generate_fallback_questions(self) -> List[Dict]:
        """Generate fallback questions if parsing fails"""
        return [
            {
                "question": "Based on the material, what is the main concept discussed?",
                "options": [
                    "A) Concept A",
                    "B) Concept B",
                    "C) Concept C",
                    "D) Concept D"
                ],
                "correct_answer": "A) Concept A",
                "explanation": "This is a placeholder question. Please regenerate."
            }
        ]
