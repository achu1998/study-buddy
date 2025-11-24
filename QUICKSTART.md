# Quick Start Guide for StudyBuddy

## Setup (5 minutes)

### Step 1: Install Ollama
1. Download from https://ollama.com
2. Install for your operating system
3. Open terminal/command prompt

### Step 2: Download a Model
```bash
# Choose ONE model:
ollama pull llama2:13b      # Recommended (7.3GB)
# OR
ollama pull mistral:7b      # Faster (4.1GB)
```

### Step 3: Verify Ollama
```bash
ollama list
# Should show your downloaded model
```

### Step 4: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Run the App
```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## Using StudyBuddy

### 1. Chat with AI Tutor
- Go to **Chat** tab
- Ask questions about your coursework
- Get guided learning (not direct answers)

### 2. Upload & Summarize PDFs
- Click "Browse files" in sidebar
- Upload your course material PDF
- Click "📝 Summarize"
- View summary in **Summary** tab

### 3. Generate Practice Tests
- Upload a PDF with course material
- Click "❓ Generate MCQ"
- Go to **MCQ Test** tab
- Answer questions and submit

## Tips

### Getting Good Responses
- Be specific in your questions
- Share what you've tried
- Ask about concepts, not just answers

### Working with PDFs
- Use text-based PDFs (not scanned images)
- Smaller PDFs work faster (< 50 pages)
- Material should be in English

### Managing Sessions
- Click "🔄 New Session" to start fresh
- Use "📥 Export Chat" to save conversations

## Troubleshooting

**App won't start?**
- Check Ollama is running: `ollama list`
- Verify Python version: `python --version` (need 3.8+)

**Slow responses?**
- Use a smaller model: `mistral:7b`
- Upload smaller PDFs
- Ask shorter questions

**PDF won't process?**
- Ensure it's not password-protected
- Check it's a real PDF (not image scan)
- Try a different PDF

## What StudyBuddy Does

✅ Guides your learning through questions
✅ Provides frameworks and structure
✅ Helps you understand concepts
✅ Creates study materials from your PDFs

❌ Does NOT give direct answers
❌ Does NOT complete homework for you
❌ Does NOT write full essays

## Next Steps

1. Upload a PDF from your course
2. Get it summarized
3. Generate practice questions
4. Chat about concepts you're learning

**Remember**: StudyBuddy helps you learn, it doesn't do the work for you!
