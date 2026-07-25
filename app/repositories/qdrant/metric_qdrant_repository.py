# 负责实现qdrant中metric相关集合的读写操作
from typing import List
from dataclasses import asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.conf.app_config import app_config
from app.entities.column_info import ColumnInfo


class MetricQdrantRepository:
    # Qdrant 集合名称
    COLLECTION_NAME: str = "data-agent-column"

    def __init__(self, client: AsyncQdrantClient):
        self.client: AsyncQdrantClient = client

    async def ensure_collection(self) -> None:
        """检查集合是否存在，不存在则创建向量集合"""
        if not await self.client.collection_exists(self.COLLECTION_NAME):
            await self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE
                )
            )

    async def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        payloads: List[ColumnInfo],
        batch_size: int = 20
    ) -> None:
        """
        批量写入向量数据
        :param ids: 数据唯一ID列表
        :param embeddings: 向量数组列表
        :param payloads: 字段元数据实体列表
        :param batch_size: 单批写入条数
        """
        # 空数据直接返回，避免无效请求
        if not all((ids, embeddings, payloads)):
            return

        zipped_data = list(zip(ids, embeddings, payloads))
        # 分片批量写入
        for start in range(0, len(zipped_data), batch_size):
            batch = zipped_data[start: start + batch_size]
            points = [
                PointStruct(
                    id=item_id,
                    vector=embedding,
                    payload=asdict(payload)
                )
                for item_id, embedding, payload in batch
            ]
            await self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points
            )