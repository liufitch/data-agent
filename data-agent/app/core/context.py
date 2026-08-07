# 负责定义异步任务上下文变量

import uuid
from contextvars import ContextVar

# 上下文变量定义
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="unknown")


def get_request_id() -> str:
    """获取当前链路请求ID"""
    return request_id_ctx_var.get()


def set_request_id(req_id: str) -> None:
    """设置当前链路请求ID"""
    request_id_ctx_var.set(req_id)


def generate_request_id() -> str:
    """生成UUID格式请求ID"""
    return str(uuid.uuid4())