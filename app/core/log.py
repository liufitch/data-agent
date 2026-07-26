import asyncio
import sys
from pathlib import Path

from loguru import logger

from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var

# 日志格式（保留原有样式）
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>request_id - {extra[request_id]}</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 【核心】日志过滤器：每条日志触发时动态获取当前协程的 request_id
def log_filter(record):
    # 动态从上下文变量取值，异步隔离不串号
    record["extra"]["request_id"] = request_id_ctx_var.get()
    return True

# 清空默认处理器
logger.remove()

# 控制台日志
if app_config.logging.console.enable:
    logger.add(
        sink=sys.stdout,
        level=app_config.logging.console.level,
        format=log_format,
        filter=log_filter  # 挂载过滤器
    )

# 文件日志
if app_config.logging.file.enable:
    log_path = Path(app_config.logging.file.path)
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        sink=log_path / "app.log",
        level=app_config.logging.file.level,
        format=log_format,
        filter=log_filter,  # 挂载过滤器
        rotation=app_config.logging.file.rotation,
        retention=app_config.logging.file.retention,
        encoding="utf-8"
    )

# ------------------- 测试代码 -------------------
if __name__ == '__main__':
    async def graph(request: str):
        logger.info(f"执行业务逻辑: {request}")

    async def test1():
        request_id_ctx_var.set("request-1")
        logger.info("test1 开始处理")
        await asyncio.sleep(1)
        await graph("request-1")

    async def test2():
        request_id_ctx_var.set("request-2")
        logger.info("test2 开始处理")
        await asyncio.sleep(1)
        await graph("request-2")

    async def main():
        await asyncio.gather(test1(), test2())

    asyncio.run(main())