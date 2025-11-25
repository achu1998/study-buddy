# StudyBuddy - Local AI Learning Assistant

A Streamlit-based AI tutor that guides students through Socratic questioning and scaffolding, with PDF processing, summarization, and MCQ generation capabilities.

## Features

- 📚 **PDF Upload & Processing**: Extract text from course materials
- 📝 **Intelligent Summarization**: Generate concise summaries of uploaded content
- ❓ **MCQ Generation**: Create practice tests from course materials
- 💬 **Socratic Chat Interface**: Get guided learning support through 5-tier response system
- 🗄️ **Conversation History**: All chats are persisted in SQLite database
- 📥 **Session Export**: Download conversation history in JSON format
- 🎯 **Learning Tiers**: Adaptive guidance from clarification to resource pointers

## Architecture

### Response Tier System
1. **Tier 1 (Clarification)**: Define terminology and concepts
2. **Tier 2 (Scaffolding)**: Break down problems into components
3. **Tier 3 (Skeleton Code)**: Provide structure with TODOs
4. **Tier 4 (Process Hints)**: Describe methodology without implementation
5. **Tier 5 (Resource Pointers)**: Suggest concepts and resources

## Prerequisites

### 1. Install Ollama
Download and install Ollama from [ollama.com](https://ollama.com)

### 2. Pull a Model
```bash
# Recommended models:
ollama pull llama2:13b        # Best balance (7.3GB)
ollama pull mistral:7b        # Faster, smaller (4.1GB)
ollama pull deepseek-r1:7b    # Best for STEM (4.7GB)
```

### 3. Verify Ollama is Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Expected response: JSON with available models
```

## Installation

### 1. Clone/Download Files
Place all files in the same directory:
```
study-buddy/
├── streamlit_app.py
├── ollama_client.py
├── prompts.py
├── pdf_processor.py
├── database.py
├── requirements.txt
└── README.md
```

### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv study-buddy

# Activate on Windows
study-buddy\Scripts\activate

# Activate on macOS/Linux
source study-buddy/bin/activate

# Deactivate
deactivate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the Application

### 1. Ensure Ollama is Running
The Ollama service should be running on `http://localhost:11434`

### 2. Start Streamlit
```bash
streamlit run streamlit_app.py
```

### 3. Access the Application
- The app will open automatically in your browser
- Default URL: `http://localhost:8501`

## Usage Guide

### Chat Interface
1. Navigate to the **Chat** tab
2. Type your question in the input box
3. StudyBuddy will respond with guidance (not direct answers)
4. Continue the conversation to deepen understanding

### PDF Upload & Summarization
1. Click "Browse files" in the sidebar
2. Upload a PDF of your course material
3. Click "📝 Summarize" to generate a summary
4. View the summary in the **Summary** tab

### MCQ Test Generation
1. Upload a PDF with course material
2. Click "❓ Generate MCQ" in the sidebar
3. Navigate to the **MCQ Test** tab
4. Answer the questions and click "✅ Submit Answers"
5. Review your score and explanations

### Session Management
- **New Session**: Clear chat and start fresh
- **Export Chat**: Download conversation as JSON

## Configuration

### Changing the Model
Edit `ollama_client.py`:
```python
def __init__(self, base_url: str = "http://localhost:11434", 
             model: str = "llama2:13b"):  # Change model here
```

### Adjusting Response Length
Edit `prompts.py` to modify word limits:
```python
- Per response: 200-300 words max
- Code snippets: 15-20 lines max
```

### Database Location
Edit `database.py`:
```python
def __init__(self, db_path: str = "study_buddy.db"):  # Change path here
```

## File Structure

### `study_buddy.py`
Main application file with UI and orchestration logic

### `ollama_client.py`
Handles all communication with Ollama API:
- Chat response generation
- Tier classification
- Summary generation
- MCQ creation
- Guardrails against complete solutions

### `prompts.py`
System prompts for different functions:
- Socratic tutoring prompt
- Summarization prompt
- MCQ generation prompt

### `pdf_processor.py`
PDF text extraction and cleaning:
- Extract text from uploaded PDFs
- Clean and format extracted text
- Extract metadata

### `database.py`
SQLite database operations:
- Conversation persistence
- Message history
- Course material storage
- Learning metrics tracking

## Troubleshooting

### "Cannot connect to Ollama"
- Ensure Ollama is installed and running
- Check `http://localhost:11434` in your browser
- Restart Ollama service

### "Request timed out"
- The model is taking too long to respond
- Try a smaller model (e.g., `mistral:7b`)
- Reduce the PDF size or text length

### "Error extracting text from PDF"
- Ensure PDF is not password-protected
- Try a different PDF
- Some PDFs (scanned images) may not have extractable text

### Database Errors
- Delete `study_buddy.db` to reset the database
- Check file permissions in the directory

## Performance Tips

### For Faster Responses
1. Use smaller models: `mistral:7b` or `deepseek-r1:7b`
2. Reduce context window (fewer conversation turns)
3. Limit PDF size to < 100 pages

### For Better Quality
1. Use larger models: `llama2:13b` or `phi:14b`
2. Increase temperature for more creative responses
3. Provide more context in your questions

## Academic Integrity

StudyBuddy is designed to **guide learning**, not provide direct answers:
- ✅ Provides scaffolding and frameworks
- ✅ Asks clarifying questions
- ✅ Offers process guidance
- ❌ Does NOT give complete solutions
- ❌ Does NOT write full essays
- ❌ Does NOT provide direct homework answers

Students should cite StudyBuddy usage in their work:
```
"Using StudyBuddy AI tutor (Session ID: xyz), November 21, 2025"
```

## Privacy & Data

- **All data is local**: Nothing leaves your machine
- **No external API calls**: Ollama runs entirely offline
- **Database is local**: SQLite file in your directory
- **Export anytime**: Download your conversation history

## Advanced Configuration

### Environment Variables
Create a `.env` file:
```bash
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama2:13b
DATABASE_PATH=study_buddy.db
MAX_CONTEXT_TOKENS=4096
```

### Custom System Prompts
Edit `prompts.py` to customize the tutoring behavior

### Adding More Features
- Multi-language support
- Voice input/output
- Diagram generation
- Collaborative study sessions

## System Requirements

- **OS**: Windows 10+, macOS 10.15+, or Linux
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 10GB for models
- **Python**: 3.8 or higher

## Model Recommendations

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `llama2:13b` | 7.3GB | Medium | Balanced quality and speed |
| `mistral:7b` | 4.1GB | Fast | Quick responses |
| `deepseek-r1:7b` | 4.7GB | Medium | STEM subjects |
| `phi:14b` | 9.1GB | Slow | Highest quality |

## Known Limitations

1. **PDF Processing**: Cannot extract text from scanned images
2. **Context Window**: Limited to ~4000 tokens per conversation
3. **MCQ Parsing**: May occasionally fail to parse complex questions
4. **Offline Only**: Requires Ollama to be running locally

## Contributing

This is a research/educational project. Improvements welcome:
- Better PDF parsing
- Multi-modal support (images, diagrams)
- Enhanced MCQ generation
- Learning analytics dashboard

## License

Educational and research use only. Based on the StudyBuddy implementation guide.

## Support

For issues or questions:
1. Check Ollama is running: `ollama list`
2. Verify Python dependencies: `pip list`
3. Check logs in terminal where Streamlit is running

## Acknowledgments

Based on the pedagogical framework from the StudyBuddy implementation guide, designed to support learning through Socratic questioning and scaffolding.
