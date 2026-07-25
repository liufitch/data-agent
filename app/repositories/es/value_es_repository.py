# 用于定义es中value索引的实体类

from typing import List
from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.entities.value_info import ValueInfo


class ValueESRepository:
    # ES 索引名称 & 映射配置（常量规范）
    INDEX_NAME: str = "data-agent-value"
    INDEX_MAPPINGS: dict = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client: AsyncElasticsearch = client

    async def ensure_index(self) -> None:
        """检查索引是否存在，不存在则创建并应用映射"""
        if not await self.client.indices.exists(index=self.INDEX_NAME):
            await self.client.indices.create(
                index=self.INDEX_NAME,
                mappings=self.INDEX_MAPPINGS
            )

    async def index(self, value_infos: List[ValueInfo], batch_size: int = 20) -> None:
        """
        批量写入字段取值数据到 ES
        :param value_infos: 字段取值实体列表
        :param batch_size: 单批 bulk 大小
        """
        # 空数据直接拦截
        if not value_infos:
            return
        # 校验批次大小合法性
        if batch_size <= 0:
            raise ValueError("batch_size 必须为正整数")

        for start in range(0, len(value_infos), batch_size):
            batch = value_infos[start: start + batch_size]
            operations = []
            for info in batch:
                operations.append({"index": {"_index": self.INDEX_NAME, "_id": info.id}})
                operations.append(asdict(info))

            await self.client.bulk(operations=operations)