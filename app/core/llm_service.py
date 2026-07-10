import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

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
                api_key=self.api_key,
            )

            print(f"🤖 LLM initialized: {self.model_name} (temp={self.temperature})")
            return llm

        except ImportError:
            raise ImportError("langchain-openai package is required. Install with: pip install langchain-openai")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM: {str(e)}")

    async def query(self, prompt: str, session_id: str | None = None) -> str:
        try:
            message = HumanMessage(content=prompt)

            if session_id and self.callbacks:
                for callback in self.callbacks:
                    if hasattr(callback, "session_id"):
                        callback.session_id = session_id

            response = await self._llm.ainvoke([message], config={"callbacks": self.callbacks})

            if hasattr(response, "content"):
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

    async def generate_project_summary(self, top_risk_evidences: list[dict], project_name: str) -> str:
        """Generate a concise project summary based on the most important risk evidences."""

        # Build evidence text for the prompt
        evidence_sections = []
        for risk_data in top_risk_evidences:
            risk_type = risk_data["risk_type"]
            score = risk_data["score"]
            evidences = risk_data["evidences"]

            if evidences:
                evidence_texts = [f"• {evidence}" for evidence in evidences]
                evidence_section = f"**{risk_type}** (Risk Score: {score:.2f}):\n" + "\n".join(evidence_texts)
                evidence_sections.append(evidence_section)

        all_evidences = "\n\n".join(evidence_sections)

        prompt = f"""You are analyzing a carbon credit project for risk assessment. Based on the most significant risk evidences found in the project documents, create a concise summary that highlights the key risk factors.

Project: {project_name}

Key Risk Evidences:
{all_evidences}

Instructions:
- Write a 1-3 sentence summary that captures the most important risk concerns
- Focus on the highest-impact findings that would be most relevant for decision-making
- Use clear, professional language suitable for stakeholders
- Avoid technical jargon where possible
- Be specific about the risks rather than generic

Summary:"""

        return await self.query(prompt, session_id=f"project_summary_{project_name}")


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def simple_llm_test() -> str:
    llm_service = get_llm_service()
    return await llm_service.query("Hello AI, give some short answer")
