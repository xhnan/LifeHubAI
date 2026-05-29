from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

try:
    from langchain_deepseek import ChatDeepSeek
except Exception:
    ChatDeepSeek = None

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None


zhipu_api_key = os.getenv("ZHIPU_API_KEY")


def zhipu_llm(temperature: float = 0.6):
    if ChatOpenAI is None:
        raise RuntimeError("langchain-openai is not installed")
    return ChatOpenAI(
        temperature=temperature,
        model="glm-5",
        openai_api_key=zhipu_api_key,
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
    )


def deepseek_llm(temperature: float = 0.6):
    if ChatDeepSeek is None:
        raise RuntimeError("langchain-deepseek is not installed")
    return ChatDeepSeek(
        temperature=temperature,
        model="deepseek-chat",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    )


def deepseek_llm_reasoner(temperature: float = 0.6):
    if ChatDeepSeek is None:
        raise RuntimeError("langchain-deepseek is not installed")
    return ChatDeepSeek(
        temperature=temperature,
        model="deepseek-reasoner",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    )
