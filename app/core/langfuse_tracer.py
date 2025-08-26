import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_langfuse_callback():
    # Check if Langfuse is configured
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST")
    
    if not public_key or not secret_key:
        print("⚠️  Langfuse not configured (missing keys), skipping tracing")
        return None
    
    try:
        from langfuse.langchain import CallbackHandler
        
        # In v3, CallbackHandler uses global configuration
        # Configuration is handled via environment variables or Langfuse() client init
        langfuse_handler = CallbackHandler()
        
        print("🔍 Langfuse tracing enabled")
        return langfuse_handler
        
    except ImportError:
        print("⚠️  Langfuse not installed, skipping tracing")
        return None
    except Exception as e:
        print(f"⚠️  Failed to initialize Langfuse: {e}")
        return None


def get_langchain_callbacks() -> list:
    callbacks = []
    
    # Add Langfuse callback if available
    langfuse_callback = get_langfuse_callback()
    if langfuse_callback:
        callbacks.append(langfuse_callback)
    
    return callbacks 