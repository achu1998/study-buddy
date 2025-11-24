# StudyBuddy Streamlit Application
# Main application file with PDF processing, summarization, and MCQ generation

import streamlit as st
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Tuple
import hashlib

# Import local modules
from ollama_client import OllamaClient
from prompts import (
    STUDY_BUDDY_SYSTEM_PROMPT,
    get_tier_selection_prompt,
    get_summarization_prompt,
    get_mcq_generation_prompt
)
from pdf_processor import PDFProcessor
from database import Database

# Page configuration
st.set_page_config(
    page_title="StudyBuddy - AI Learning Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #1976d2;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 5px solid #4caf50;
    }
    .tier-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: bold;
        margin-top: 0.5rem;
    }
    .tier-1 { background-color: #e3f2fd; color: #1976d2; }
    .tier-2 { background-color: #e8f5e9; color: #388e3c; }
    .tier-3 { background-color: #fff3e0; color: #f57c00; }
    .tier-4 { background-color: #fce4ec; color: #c2185b; }
    .tier-5 { background-color: #f3e5f5; color: #7b1fa2; }
    .citation-tag {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        margin: 0.2rem;
        background-color: #fff9c4;
        border-radius: 0.3rem;
        font-size: 0.8rem;
    }
    .summary-box {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    .mcq-container {
        background-color: #f5f5f5;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .mcq-question {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'ollama_client' not in st.session_state:
        st.session_state.ollama_client = OllamaClient()
    if 'db' not in st.session_state:
        st.session_state.db = Database()
    if 'pdf_processor' not in st.session_state:
        st.session_state.pdf_processor = PDFProcessor()
    if 'course_material' not in st.session_state:
        st.session_state.course_material = None
    if 'material_summary' not in st.session_state:
        st.session_state.material_summary = None
    if 'mcq_questions' not in st.session_state:
        st.session_state.mcq_questions = []
    if 'mcq_answers' not in st.session_state:
        st.session_state.mcq_answers = {}
    if 'show_mcq_results' not in st.session_state:
        st.session_state.show_mcq_results = False

initialize_session_state()

# Sidebar for course material management
with st.sidebar:
    st.markdown("### 📚 Course Material")
    
    uploaded_file = st.file_uploader(
        "Upload PDF Course Material",
        type=['pdf'],
        help="Upload your course material to get summaries and practice tests"
    )
    
    if uploaded_file is not None:
        # Process uploaded PDF
        with st.spinner("Processing PDF..."):
            try:
                pdf_text = st.session_state.pdf_processor.extract_text(uploaded_file)
                
                if pdf_text:
                    st.session_state.course_material = pdf_text
                    st.success(f"✅ Processed {len(pdf_text)} characters")
                    
                    # Show preview
                    with st.expander("📄 Preview"):
                        st.text(pdf_text[:500] + "...")
                else:
                    st.error("Could not extract text from PDF")
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
    
    # Material actions
    if st.session_state.course_material:
        st.markdown("---")
        st.markdown("### 🎯 Material Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝 Summarize", use_container_width=True):
                with st.spinner("Generating summary..."):
                    try:
                        summary = st.session_state.ollama_client.generate_summary(
                            st.session_state.course_material
                        )
                        st.session_state.material_summary = summary
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating summary: {str(e)}")
        
        with col2:
            if st.button("❓ Generate MCQ", use_container_width=True):
                with st.spinner("Creating questions..."):
                    try:
                        questions = st.session_state.ollama_client.generate_mcq(
                            st.session_state.course_material
                        )
                        st.session_state.mcq_questions = questions
                        st.session_state.mcq_answers = {}
                        st.session_state.show_mcq_results = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating MCQ: {str(e)}")
    
    # Session management
    st.markdown("---")
    st.markdown("### ⚙️ Session")
    
    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.material_summary = None
        st.session_state.mcq_questions = []
        st.session_state.mcq_answers = {}
        st.session_state.show_mcq_results = False
        st.rerun()
    
    if st.button("📥 Export Chat", use_container_width=True):
        if st.session_state.messages:
            export_data = {
                "session_id": st.session_state.session_id,
                "timestamp": datetime.now().isoformat(),
                "messages": st.session_state.messages
            }
            st.download_button(
                label="Download JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"study_buddy_{st.session_state.session_id[:8]}.json",
                mime="application/json"
            )

# Main content area
st.markdown('<p class="main-header">📚 StudyBuddy - AI Learning Assistant</p>', 
            unsafe_allow_html=True)

# Create tabs for different features
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Summary", "❓ MCQ Test"])

# Tab 1: Chat Interface
with tab1:
    st.markdown("### Chat with StudyBuddy")
    st.markdown("Ask questions and get guided learning support. Remember, I'm here to guide you, not give you direct answers!")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for idx, message in enumerate(st.session_state.messages):
            role = message["role"]
            content = message["content"]
            
            message_class = "user-message" if role == "user" else "assistant-message"
            
            st.markdown(f'<div class="chat-message {message_class}">', 
                       unsafe_allow_html=True)
            
            st.markdown(f"**{'You' if role == 'user' else 'StudyBuddy'}:**")
            st.markdown(content)
            
            # Show tier badge for assistant messages
            if role == "assistant" and "tier" in message:
                tier = message["tier"]
                st.markdown(
                    f'<span class="tier-badge tier-{tier}">Guidance Tier {tier}</span>',
                    unsafe_allow_html=True
                )
            
            # Show citations if present
            if role == "assistant" and message.get("citations"):
                st.markdown("**Citations:**")
                citations_html = "".join([
                    f'<span class="citation-tag">{c["id"]}: {c.get("concept", "Reference")}</span>'
                    for c in message["citations"]
                ])
                st.markdown(citations_html, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Ask a question or share what you're working on...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save to database
        st.session_state.db.add_message(
            st.session_state.session_id,
            "user",
            user_input
        )
        
        # Generate response
        with st.spinner("StudyBuddy is thinking..."):
            try:
                response_text, tier, citations = st.session_state.ollama_client.generate_chat_response(
                    session_id=st.session_state.session_id,
                    user_message=user_input,
                    conversation_history=st.session_state.messages,
                    course_context=st.session_state.course_material
                )
                
                # Add assistant message
                assistant_msg = {
                    "role": "assistant",
                    "content": response_text,
                    "tier": tier,
                    "citations": citations,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.messages.append(assistant_msg)
                
                # Save to database
                st.session_state.db.add_message(
                    st.session_state.session_id,
                    "assistant",
                    response_text,
                    response_tier=tier,
                    citations=citations
                )
                
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
        
        st.rerun()

# Tab 2: Summary View
with tab2:
    st.markdown("### 📝 Course Material Summary")
    
    if st.session_state.course_material is None:
        st.info("👈 Upload a PDF in the sidebar to generate a summary")
    elif st.session_state.material_summary is None:
        st.info("Click 'Summarize' in the sidebar to generate a summary of your course material")
    else:
        st.markdown('<div class="summary-box">', unsafe_allow_html=True)
        st.markdown("#### Key Points")
        st.markdown(st.session_state.material_summary)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Option to refine summary
        if st.button("🔄 Regenerate Summary"):
            with st.spinner("Regenerating summary..."):
                try:
                    summary = st.session_state.ollama_client.generate_summary(
                        st.session_state.course_material
                    )
                    st.session_state.material_summary = summary
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Tab 3: MCQ Test
with tab3:
    st.markdown("### ❓ Multiple Choice Questions")
    
    if st.session_state.course_material is None:
        st.info("👈 Upload a PDF in the sidebar to generate questions")
    elif not st.session_state.mcq_questions:
        st.info("Click 'Generate MCQ' in the sidebar to create practice questions")
    else:
        st.markdown(f"**Total Questions: {len(st.session_state.mcq_questions)}**")
        
        # Display questions
        for idx, q in enumerate(st.session_state.mcq_questions):
            st.markdown(f'<div class="mcq-container">', unsafe_allow_html=True)
            st.markdown(f'<p class="mcq-question">Q{idx+1}. {q["question"]}</p>', 
                       unsafe_allow_html=True)
            
            # Radio buttons for options
            answer_key = f"q_{idx}"
            selected = st.radio(
                "Select your answer:",
                options=q["options"],
                key=answer_key,
                index=None,
                disabled=st.session_state.show_mcq_results
            )
            
            if selected:
                st.session_state.mcq_answers[idx] = selected
            
            # Show correct answer if results are shown
            if st.session_state.show_mcq_results:
                correct_answer = q["correct_answer"]
                user_answer = st.session_state.mcq_answers.get(idx, "")
                
                if user_answer == correct_answer:
                    st.success(f"✅ Correct! Answer: {correct_answer}")
                else:
                    st.error(f"❌ Incorrect. Your answer: {user_answer}")
                    st.info(f"Correct answer: {correct_answer}")
                
                if q.get("explanation"):
                    with st.expander("💡 Explanation"):
                        st.markdown(q["explanation"])
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if not st.session_state.show_mcq_results:
                if st.button("✅ Submit Answers", type="primary", use_container_width=True):
                    if len(st.session_state.mcq_answers) < len(st.session_state.mcq_questions):
                        st.warning("Please answer all questions before submitting")
                    else:
                        st.session_state.show_mcq_results = True
                        st.rerun()
        
        with col2:
            if st.button("🔄 New Test", use_container_width=True):
                with st.spinner("Creating new questions..."):
                    try:
                        questions = st.session_state.ollama_client.generate_mcq(
                            st.session_state.course_material
                        )
                        st.session_state.mcq_questions = questions
                        st.session_state.mcq_answers = {}
                        st.session_state.show_mcq_results = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # Show results summary
        if st.session_state.show_mcq_results:
            st.markdown("---")
            correct_count = sum(
                1 for idx, q in enumerate(st.session_state.mcq_questions)
                if st.session_state.mcq_answers.get(idx) == q["correct_answer"]
            )
            total = len(st.session_state.mcq_questions)
            percentage = (correct_count / total) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Correct Answers", f"{correct_count}/{total}")
            with col2:
                st.metric("Score", f"{percentage:.1f}%")
            with col3:
                if percentage >= 80:
                    st.success("🌟 Excellent!")
                elif percentage >= 60:
                    st.info("👍 Good job!")
                else:
                    st.warning("📚 Keep studying!")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>StudyBuddy v1.0 - Your AI Learning Partner</p>
    <p>Remember: This tool guides your learning, it doesn't do the work for you!</p>
</div>
""", unsafe_allow_html=True)
