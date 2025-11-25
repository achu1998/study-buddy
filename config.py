import os
from dotenv import load_dotenv

load_dotenv()

# Deployment mode
DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "local")  # "local" or "cloud"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
# LLM Configuration
if DEPLOYMENT_MODE == "cloud":
    # Use OpenAI, Anthropic, or other cloud APIs
    API_KEY = os.getenv("API_KEY", "")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
else:
    # Use local Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
