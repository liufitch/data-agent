# 负责定义FastAPI声明周期事件

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.log import logger
# 客户端管理器
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动：初始化所有客户端与连接
    关闭：统一释放所有资源连接
    """
    logger.info("开始初始化客户端连接...")
    # 应用启动阶段
    # embedding_client_manager.init()
    # qdrant_client_manager.init()
    # es_client_manager.init()
    # meta_mysql_client_manager.init()
    # dw_mysql_client_manager.init()
    logger.info("所有客户端初始化完成")
    yield

    # 应用关闭阶段，确保资源有序释放
    logger.info("开始释放客户端资源...")
    await qdrant_client_manager.close()
    await es_client_manager.close()
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await embedding_client_manager.close()
    logger.info("所有资源释放完毕，应用即将退出")