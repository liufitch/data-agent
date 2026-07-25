# 负责定义llm
from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

def create_llm():
    """创建 LLM 实例"""
    return init_chat_model(
        model=app_config.llm.model_name,
        model_provider="openai",
        api_key=app_config.llm.api_key,
        base_url=app_config.llm.base_url,
        temperature=0.0
    )

# 全局单例
llm = create_llm()