# Ollama Client for local LLM integration
# Handles all interactions with the Ollama API

import httpx
import asyncio
import json
import re
from typing import List, Dict, Tuple
from prompts import (
    STUDY_BUDDY_SYSTEM_PROMPT,
    get_tier_selection_prompt,
    get_summarization_prompt,
    get_mcq_generation_prompt
)

class OllamaClient:
    """Client for interacting with local Ollama models"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        self.base_url = base_url
        self.model = model
        self.timeout = 600.0  # 10 minutes for longer responses
    
    def _make_request(self, prompt: str, system: str, temperature: float = 0.3, 
                     max_tokens: int = 500) -> str:
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

        For each question, provide:
        1. A clear question
        2. Four options (A, B, C, D)
        3. The correct answer
        4. A brief explanation

        Format each question exactly as:
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
        """Parse MCQ response text into structured format"""
        
        questions = []
        
        # Split by question delimiter
        question_blocks = response.split('---')
        
        for block in question_blocks:
            if not block.strip():
                continue
            
            # Extract components using regex
            question_match = re.search(r'QUESTION:\s*(.+?)(?=\n[A-D]\))', block, re.DOTALL)
            
            options_matches = re.findall(r'([A-D])\)\s*(.+?)(?=\n[A-D]\)|CORRECT:|$)', block, re.DOTALL)
            
            correct_match = re.search(r'CORRECT:\s*([A-D])', block)
            explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?=QUESTION:|---|\Z)', block, re.DOTALL)
            
            if question_match and options_matches and correct_match:
                question_text = question_match.group(1).strip()
                
                options = [f"{letter}) {text.strip()}" for letter, text in options_matches]
                
                correct_letter = correct_match.group(1)
                correct_answer = next(
                    (opt for opt in options if opt.startswith(correct_letter)),
                    options[0]  # Fallback
                )
                
                explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided."
                
                questions.append({
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": explanation
                })
        
        # If parsing failed, generate fallback questions
        if not questions:
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
