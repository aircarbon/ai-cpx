import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.core.langfuse_tracer import get_langchain_callbacks

# Load environment variables
load_dotenv()


class LLMService:
    
    def __init__(self):
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "1"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2048"))
        self.timeout = int(os.getenv("OPENAI_TIMEOUT", "120"))
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Get Langfuse callbacks for tracing
        self.callbacks = get_langchain_callbacks()
        
        # Initialize LangChain LLM
        self._llm = self._initialize_llm()
    
    def _initialize_llm(self):
        try:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                api_key=self.api_key
            )
            
            print(f"🤖 LLM initialized: {self.model_name} (temp={self.temperature})")
            return llm
            
        except ImportError:
            raise ImportError("langchain-openai package is required. Install with: pip install langchain-openai")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM: {str(e)}")
    
    async def query(self, prompt: str, session_id: Optional[str] = None) -> str:
        try:
            message = HumanMessage(content=prompt)
            
            if session_id and self.callbacks:
                for callback in self.callbacks:
                    if hasattr(callback, 'session_id'):
                        callback.session_id = session_id
            
            response = await self._llm.ainvoke(
                [message], 
                config={"callbacks": self.callbacks}
            )
            
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            print(f"❌ LLM query failed: {str(e)}")
            raise
    
    async def analyze_risk(self, chunk_content: str, risk_type: str, risk_description: str) -> str:
        prompt = f"""
        Please analyze the following text for {risk_type} risks.
        
        Risk Type: {risk_type}
        Risk Description: {risk_description}
        
        Text to analyze:
        {chunk_content}
        
        Please provide a brief risk assessment.
        """
        
        return await self.query(prompt, session_id=f"risk_analysis_{risk_type}")


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def simple_llm_test() -> str:
    llm_service = get_llm_service()
    return await llm_service.query("Hello AI, give some short answer")
