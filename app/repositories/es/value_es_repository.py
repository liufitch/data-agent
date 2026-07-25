# 用于定义es中value索引的实体类

from typing import List
from dataclasses import asdict
from app.core.log import logger
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

    async def search(
            self,
            keyword: str,
            score_threshold: float = 0.6,
            limit: int = 5
    ) -> List[ValueInfo]:
        """
        根据关键词检索 ES 中的字段取值数据
        :param keyword: 检索关键词
        :param score_threshold: 最小匹配分数阈值
        :param limit: 最大返回条数
        :return: 匹配的 ValueInfo 实体列表
        """
        # 空关键词直接返回空列表
        keyword = keyword.strip()
        if not keyword:
            logger.warning("检索关键词为空，跳过 ES 查询")
            return []

        # 参数合法性校验与修正
        if limit <= 0:
            logger.warning(f"非法 limit 值 {limit}，已重置为默认值 5")
            limit = 5
        if score_threshold < 0.0:
            logger.warning(f"非法分数阈值 {score_threshold}，已重置为默认值 0.6")
            score_threshold = 0.6

        try:
            result = await self.client.search(
                index=self.INDEX_NAME,
                query={
                    "match": {
                        "value": keyword
                    }
                },
                min_score=score_threshold,
                size=limit
            )

            # 解析命中数据并转为实体
            return [ValueInfo(**hit["_source"]) for hit in result["hits"]["hits"]]
        except Exception:
            logger.exception("ES 字段取值检索异常")
            return []