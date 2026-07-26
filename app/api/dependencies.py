# 负责定义查询接口依赖项

from typing import Annotated
from fastapi import Depends
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

# 客户端管理器
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager

# 数据仓库
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

# 业务服务
from app.services.query_service import QueryService

# ------------------------------
# 数据库会话依赖
# ------------------------------
async def get_meta_session() -> AsyncSession:
    """元数据 MySQL 异步会话"""
    async with meta_mysql_client_manager.session_factory() as session:
        yield session

async def get_dw_session() -> AsyncSession:
    """数仓 MySQL 异步会话"""
    async with dw_mysql_client_manager.session_factory() as session:
        yield session

# ------------------------------
# 客户端 & 仓库依赖
# ------------------------------
async def get_embedding_client() -> HuggingFaceEndpointEmbeddings:
    """获取向量化客户端"""
    return embedding_client_manager.client

async def get_column_qdrant_repo() -> ColumnQdrantRepository:
    """获取字段向量仓库"""
    return ColumnQdrantRepository(qdrant_client_manager.client)

async def get_metric_qdrant_repo() -> MetricQdrantRepository:
    """获取指标向量仓库"""
    return MetricQdrantRepository(qdrant_client_manager.client)

async def get_value_es_repo() -> ValueESRepository:
    """获取字段取值 ES 仓库"""
    return ValueESRepository(es_client_manager.client)

async def get_meta_mysql_repo(
    session: Annotated[AsyncSession, Depends(get_meta_session)]
) -> MetaMySQLRepository:
    """获取元数据 MySQL 仓库"""
    return MetaMySQLRepository(session)

async def get_dw_mysql_repo(
    session: Annotated[AsyncSession, Depends(get_dw_session)]
) -> DWMySQLRepository:
    """获取数仓 MySQL 仓库"""
    return DWMySQLRepository(session)

# ------------------------------
# 顶层服务依赖
# ------------------------------
async def get_query_service(
    embedding_client: Annotated[HuggingFaceEndpointEmbeddings, Depends(get_embedding_client)],
    column_qdrant_repo: Annotated[ColumnQdrantRepository, Depends(get_column_qdrant_repo)],
    metric_qdrant_repo: Annotated[MetricQdrantRepository, Depends(get_metric_qdrant_repo)],
    value_es_repo: Annotated[ValueESRepository, Depends(get_value_es_repo)],
    meta_mysql_repo: Annotated[MetaMySQLRepository, Depends(get_meta_mysql_repo)],
    dw_mysql_repo: Annotated[DWMySQLRepository, Depends(get_dw_mysql_repo)]
) -> QueryService:
    """注入所有依赖，返回查询服务实例"""
    return QueryService(
        embedding_client=embedding_client,
        column_qdrant_repository=column_qdrant_repo,
        value_es_repository=value_es_repo,
        metric_qdrant_repository=metric_qdrant_repo,
        meta_mysql_repository=meta_mysql_repo,
        dw_mysql_repository=dw_mysql_repo
    )