import re
import requests
import logging
from typing import List, Dict, Any
from langsmith import traceable
from openai import OpenAI
from langsmith.wrappers import wrap_openai

logger = logging.getLogger(__name__)


VLLM_ENDPOINT = "http://localhost:8000/v1"
OPENAI_API_KEY = "EMPTY"
DEFAULT_MODEL = "Qwen/Qwen3-1.7B"


def call_vllm(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, timeout: int = 30, enable_thinking=False) -> str:
    """
    messages: [{"role": "user|system|assistant", "content": "..."} ...]
    returns the assistant text content (concatenated) or raises requests exceptions.
    """
    # https://docs.langchain.com/langsmith/observability-quickstart#4-trace-llm-calls
    client = wrap_openai(
        OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=VLLM_ENDPOINT,
        )
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    try:
        content = response.choices[0].message.content
        if not enable_thinking:
            content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
        return content
    except Exception as e:
        logger.exception(f"ERROR: Could not extract assistant content from VLLM response: {e}")
        return response
