from typing import List
from dataclasses import asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.entities.column_info import ColumnInfo
from app.conf.app_config import app_config
from app.core.log import logger


class ColumnQdrantRepository:
    # Qdrant 集合常量名
    COLLECTION_NAME: str = "data-agent-column"

    def __init__(self, client: AsyncQdrantClient):
        self.client: AsyncQdrantClient = client

    async def ensure_collection(self) -> None:
        """检查集合是否存在，不存在则创建"""
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
        """批量写入向量数据"""
        if not all((ids, embeddings, payloads)):
            return

        zipped_data = list(zip(ids, embeddings, payloads))
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

    async def search(
        self,
        embedding: List[float],
        score_threshold: float = 0.6,
        limit: int = 5
    ) -> List[ColumnInfo]:
        """
        向量相似度检索字段
        :param embedding: 查询向量
        :param score_threshold: 相似度阈值 [0.0, 1.0]
        :param limit: 最大返回条数
        :return: 匹配的 ColumnInfo 实体列表
        """
        # 边界校验
        if not embedding:
            logger.warning("查询向量为空，跳过检索")
            return []
        if limit <= 0:
            logger.warning(f"非法 limit 值: {limit}，已修正为 5")
            limit = 5
        if not (0.0 <= score_threshold <= 1.0):
            logger.warning(f"非法相似度阈值: {score_threshold}，已修正为 0.6")
            score_threshold = 0.6

        try:
            result = await self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=embedding,
                score_threshold=score_threshold,
                limit=limit * 4
            )
            columns = {}
            for point in result.points:
                column = ColumnInfo(**point.payload)
                columns.setdefault(column.id, column)
                if len(columns) >= limit:
                    break
            return list(columns.values())
        except Exception:
            logger.exception("Qdrant 字段检索异常")
            return []
