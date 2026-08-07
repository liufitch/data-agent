# 构建元数据知识库的入口脚本，负责解析命令行参数
import asyncio
import logging
from argparse import ArgumentParser
from pathlib import Path

# 客户端管理器
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    meta_mysql_client_manager,
    dw_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager

# 数据仓库层
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

# 业务服务
from app.services.meta_knowledge_service import MetaKnowledgeService

logger = logging.getLogger(__name__)


async def build(config_path: Path):
    # 1. 统一初始化所有客户端
    logger.info("开始初始化各类客户端...")
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    logger.info("客户端初始化完成")

    try:
        # 2. 异步数据库会话 + 仓库/服务实例构建
        async with (
            meta_mysql_client_manager.session_factory() as meta_session,
            dw_mysql_client_manager.session_factory() as dw_session,
        ):
            # 实例化 Repository
            meta_repo = MetaMySQLRepository(meta_session)
            dw_repo = DWMySQLRepository(dw_session)
            col_qdrant_repo = ColumnQdrantRepository(qdrant_client_manager.client)
            metric_qdrant_repo = MetricQdrantRepository(qdrant_client_manager.client)
            es_repo = ValueESRepository(es_client_manager.client)
            embed_client = embedding_client_manager.client

            # 实例化业务服务并执行构建
            meta_service = MetaKnowledgeService(
                meta_mysql_repository=meta_repo,
                dw_mysql_repository=dw_repo,
                column_qdrant_repository=col_qdrant_repo,
                embedding_client=embed_client,
                value_es_repository=es_repo,
                metric_qdrant_repository=metric_qdrant_repo,
            )
            logger.info(f"开始解析配置并构建元知识库，配置路径: {config_path}")
            await meta_service.build(config_path)
            logger.info("元知识库构建执行完成")

    except Exception as e:
        logger.exception("构建元知识库过程发生异常")
        raise
    finally:
        # 3. 统一兜底关闭所有连接，无论正常/异常都会执行
        logger.info("开始释放所有客户端连接...")
        await meta_mysql_client_manager.close()
        await dw_mysql_client_manager.close()
        await qdrant_client_manager.close()
        await es_client_manager.close()
        await embedding_client_manager.close()
        logger.info("所有连接已释放")


def main():
    parser = ArgumentParser(description="元知识库构建工具")
    parser.add_argument("-c", "--conf", required=True, help="元数据YAML配置文件路径")
    args = parser.parse_args()

    # 校验配置文件
    config_path = Path(args.conf)
    if not config_path.exists() or not config_path.is_file():
        logger.error(f"配置文件不存在或不是有效文件: {config_path}")
        return

    # 运行异步入口
    asyncio.run(build(config_path))


if __name__ == "__main__":
    main()