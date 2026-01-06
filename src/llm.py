import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


VLLM_ENDPOINT = "http://localhost:8000/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen3-1.7B"


def call_vllm(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, timeout: int = 30, enable_thinking=False) -> str:
    """
    messages: [{"role": "user|system|assistant", "content": "..."} ...]
    returns the assistant text content (concatenated) or raises requests exceptions.
    """
    payload = {"model": model, "messages": messages}
    # enable/disable "thinking" per request level
    if isinstance(enable_thinking, bool):
        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}

    r = requests.post(VLLM_ENDPOINT, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    logger.debug(f"VLLM call payload: {payload}\nResponse data:{data}")
    try:
        return data['choices'][0]['message']['content']
    except Exception as e:
        logger.exception(f"ERROR: Could not extract assistant content from VLLM response: {e}")
        return data

