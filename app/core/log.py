import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from app.conf.app_config import app_config

# 日志格式模板
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

def init_logger() -> None:
    """统一初始化 Loguru 日志，幂等执行"""
    # 移除默认处理器
    logger.remove()

    log_conf = app_config.logging
    # 控制台日志
    if log_conf.console.enable:
        logger.add(
            sink=sys.stdout,
            level=log_conf.console.level.upper(),
            format=LOG_FORMAT,
            enqueue=True  # 异步日志，提升并发性能
        )

    # 文件日志
    if log_conf.file.enable:
        log_dir: Path = Path(log_conf.file.path)
        # 确保日志目录存在
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"

        logger.add(
            sink=log_file,
            level=log_conf.file.level.upper(),
            format=LOG_FORMAT,
            rotation=log_conf.file.rotation,
            retention=log_conf.file.retention,
            encoding="utf-8",
            enqueue=True,
            diagnose=False,  # 生产关闭详细堆栈，减少日志体积
            backtrace=True   # 异常时打印完整调用栈
        )

# 项目启动时执行日志初始化
init_logger()