from fastapi import FastAPI

from app.api.routers import query_router
from app.core.lifespan import lifespan
app = FastAPI()

# 注册路由
app.include_router(query_router)
app = FastAPI(lifespan=lifespan)


import uuid
from fastapi import Request
from app.core.context import request_id_ctx_var  # 导入上下文变量
import time
from app.core.log import logger

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request_id_ctx_var.set(req_id)

    start_time = time.perf_counter()
    logger.info(
        f"请求开始 | request_id: {req_id} | method: {request.method} | path: {request.url.path}"
    )

    response = await call_next(request)

    cost_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        f"请求结束 | request_id: {req_id} | status: {response.status_code} | 耗时: {cost_ms} ms"
    )
    response.headers["X-Request-Id"] = req_id

    return response