# 负责实现qdrant中column相关集合的读写操作
from typing import List
from dataclasses import asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.conf.app_config import app_config
from app.entities.column_info import ColumnInfo


class ColumnQdrantRepository:
    # 向量库集合名称
    COLLECTION_NAME: str = "data-agent-column"

    def __init__(self, client: AsyncQdrantClient):
        self.client: AsyncQdrantClient = client

    async def ensure_collection(self) -> None:
        """确保 Qdrant 集合存在，不存在则自动创建"""
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
        批量写入向量数据到 Qdrant
        :param ids: 每条向量唯一ID
        :param embeddings: 向量数组
        :param payloads: 字段元数据实体列表
        :param batch_size: 分批写入大小
        """
        # 空数据直接返回，跳过请求
        if not ids or not embeddings or not payloads:
            return

        zipped_data = list(zip(ids, embeddings, payloads))
        # 分批写入
        for idx in range(0, len(zipped_data), batch_size):
            batch = zipped_data[idx: idx + batch_size]
            points = [
                PointStruct(
                    id=item_id,
                    vector=emb,
                    payload=asdict(payload)
                )
                for item_id, emb, payload in batch
            ]
            await self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points
            )