# 负责定义查询接口

from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService

query_router = APIRouter(prefix="/api", tags=["查询分析"])


async def sse_event_generator(generator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """统一封装 SSE 事件格式"""
    async for data in generator:
        yield f"data: {data}\n\n"


@query_router.post("/query", summary="数据分析查询接口")
async def handle_query(
    body: QuerySchema,
    query_service: QueryService = Depends(get_query_service)
) -> StreamingResponse:
    """
    接收用户查询，执行数据分析流程，以 SSE 流式返回进度与结果
    """
    try:
        # 获取异步数据流
        stream = query_service.query(body.query)
        # 包装为标准 SSE
        return StreamingResponse(
            sse_event_generator(stream),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务执行异常: {str(e)}")