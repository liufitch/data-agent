import asyncio
import random
from pathlib import Path
from typing import List, Optional
import uuid

from omegaconf import OmegaConf
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance, VectorParams,PointStruct,
    KeywordIndexParams, TextIndexParams, TokenizerType
)
from app.conf.app_config import QdrantConfig, app_config
from app.conf.meta_config import MetaConfig


class QdrantClientManager:
    def __init__(self, qdrant_config: QdrantConfig):
        self._config = qdrant_config
        self._client: Optional[AsyncQdrantClient] = None

    def _get_base_url(self) -> str:
        """拼接 Qdrant 服务地址"""
        return f"http://{self._config.host}:{self._config.port}"

    def init(self) -> None:
        """同步初始化（建议在异步上下文前调用）"""
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=self._get_base_url(),
                timeout=self._config.timeout  # 建议配置超时
            )

    async def close(self) -> None:
        """关闭客户端连接"""
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> AsyncQdrantClient:
        """安全获取客户端，非空校验"""
        if self._client is None:
            raise RuntimeError("Qdrant AsyncClient 未初始化，请先调用 init()")
        return self._client


# 全局单例
qdrant_client_manager = QdrantClientManager(app_config.qdrant)


# 以下是创建collection、payload 和数据代码

COLUMN_COLL = "data-agent-column"
METRIC_COLL = "data-agent-metric"
VECTOR_DIM = 1024


def _semantic_texts(row: dict) -> List[str]:
    """提取适合短关键词召回的名称、描述和别名文本。"""
    aliases = row.get("alias") or []
    if not isinstance(aliases, list):
        aliases = [aliases]
    raw_texts = [row.get("name"), row.get("description"), *aliases]
    return list(dict.fromkeys(str(text).strip() for text in raw_texts if text and str(text).strip()))


def _point_id(collection_name: str, business_id: str, text: str) -> str:
    """同一业务数据和语义文本始终生成相同 point ID，避免重复写入。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_name}:{business_id}:{text}"))


async def _delete_business_points(collection_name: str, business_ids: List[str]) -> None:
    """覆盖写入前删除同业务 ID 的旧点，包括历史随机向量和重复点。"""
    if not business_ids:
        return
    await qdrant_client_manager.client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="id",
                        match=models.MatchAny(any=business_ids),
                    )
                ]
            )
        ),
        wait=True,
    )


async def _delete_stale_business_points(collection_name: str, business_ids: List[str]) -> None:
    """删除已不在当前元数据配置中的历史测试点。"""
    if not business_ids:
        return
    await qdrant_client_manager.client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="id",
                        match=models.MatchAny(any=business_ids),
                    )
                ]
            )
        ),
        wait=True,
    )





async def create_collection() :
    # 在 createCollection() / insert_column_info_list 函数开头添加
    client = qdrant_client_manager.client
    if client is None:
        raise RuntimeError("Qdrant AsyncClient 未初始化，请先调用 init()")

    # ========== 创建 data-agent-column ==========
    # ===================== data-agent-column =====================
    exists_column = await client.collection_exists(COLUMN_COLL)
    if not exists_column:
        print(f"开始创建集合：{COLUMN_COLL}")
        await client.create_collection(
            collection_name=COLUMN_COLL,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            on_disk_payload=True
        )
        # 创建索引
        await client.create_payload_index(
            collection_name=COLUMN_COLL,
            field_name="id",
            field_schema=KeywordIndexParams(type="keyword")
        )
        await client.create_payload_index(
            collection_name=COLUMN_COLL,
            field_name="name",
            field_schema=TextIndexParams(
                type="text",
                tokenizer=TokenizerType.WORD
            )
        )
        await client.create_payload_index(
            collection_name=COLUMN_COLL,
            field_name="table_id",
            field_schema=KeywordIndexParams(type="keyword")
        )
        print(f"✅ {COLUMN_COLL} 创建完成")
    else:
        print(f"ℹ️ 集合 {COLUMN_COLL} 已存在，跳过创建")

    # ========== 创建 data-agent-metric ==========
    exists_metric = await client.collection_exists(METRIC_COLL)
    if not exists_metric:
        print(f"开始创建集合：{METRIC_COLL}")
        await client.create_collection(
            collection_name=METRIC_COLL,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            on_disk_payload=True
        )
        await client.create_payload_index(
            collection_name=METRIC_COLL,
            field_name="id",
            field_schema=KeywordIndexParams(type="keyword")
        )
        await client.create_payload_index(
            collection_name=METRIC_COLL,
            field_name="name",
            field_schema=TextIndexParams(
                type="text",
                tokenizer=TokenizerType.WORD
            )
        )
        print(f"✅ {METRIC_COLL} 创建完成")
    else:
        print(f"ℹ️ 集合 {METRIC_COLL} 已存在，跳过创建")



    print("两个集合创建完成：data-agent-column、data-agent-metric")


async def insert_column_info_list(column_list: List[dict], embedding_func):
    """
    批量插入数据表字段元数据
    :param column_list: 原始column_info数据库记录列表
    :param embedding_func: 异步函数，输入文本str，返回向量List[float]
    """
    client = qdrant_client_manager.client
    if client is None:
        raise RuntimeError("Qdrant AsyncClient 未初始化，请先调用 init()")
    business_ids = [row["id"] for row in column_list]
    await _delete_business_points(COLUMN_COLL, business_ids)

    points = []
    for row in column_list:
        for text in _semantic_texts(row):
            # 组装文本 然后向量化
            vec = await embedding_func(text)
            points.append(PointStruct(
                id=_point_id(COLUMN_COLL, row["id"], text),
                vector=vec,
                payload=row, # payload直接存入原始字典
            ))

    # 批量upsert
    await client.upsert(
        collection_name=COLUMN_COLL,
        points=points,
        wait=True,
    )
    print(f"✅ 成功写入 {len(points)} 条字段语义向量")


async def insert_metric_info_list(metric_list: List[dict], embedding_func):
    """
    批量插入指标元数据
    :param metric_list: 原始metric_info数据库记录列表
    :param embedding_func: 异步embedding函数
    """
    client = qdrant_client_manager.client
    if client is None:
        raise RuntimeError("Qdrant AsyncClient 未初始化，请先调用 init()")
    business_ids = [row["id"] for row in metric_list]
    await _delete_business_points(METRIC_COLL, business_ids)

    points = []
    for row in metric_list:
        for text in _semantic_texts(row):
            vec = await embedding_func(text)
            points.append(PointStruct(
                id=_point_id(METRIC_COLL, row["id"], text),
                vector=vec,
                payload=row,
            ))

    await client.upsert(
        collection_name=METRIC_COLL,
        points=points,
        wait=True,
    )
    print(f"✅ 成功写入 {len(points)} 条指标语义向量")


async def run_test(collection_name: str = "my_collection", vec_size: int = 10):
    """Qdrant 读写查询测试"""
    manager = qdrant_client_manager
    client = manager.client

    try:
        # 1. 创建集合（不存在则新建）
        if not await client.collection_exists(collection_name):
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vec_size, #向量维度（如 text-embedding-ada-002=1536）
                    distance=models.Distance.COSINE #距离计算方式 Cosine 文本 Embedding（最常用）
                )
            )
            print(f"集合 {collection_name} 创建成功")

        # 2. 批量写入数据
        points = [
            models.PointStruct(
                id=i,
                vector=[random.random() for _ in range(vec_size)]
            )
            for i in range(100)
        ]
        await client.upsert(collection_name=collection_name, points=points)
        print(f"成功写入 {len(points)} 条向量数据")

        # 3. 向量检索
        query_vec = [random.random() for _ in range(vec_size)]
        result = await client.query_points(
            collection_name=collection_name,
            query=query_vec,
            limit=10,
            score_threshold=0.8
        )
        print("检索结果：")
        print(result)

    except UnexpectedResponse as e:
        print(f"Qdrant 服务请求异常: {str(e)}")
    except Exception as e:
        print(f"执行异常: {str(e)}")


async def demo(config_path: Optional[Path] = None):
    """使用真实 Embedding 将完整元数据配置写入 Qdrant。"""
    from app.clients.embedding_client_manager import embedding_client_manager

    if config_path is None:
        config_path = Path(__file__).resolve().parents[2] / "conf" / "meta_config.yaml"

    raw_config = OmegaConf.load(config_path)
    schema = OmegaConf.structured(MetaConfig)
    meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, raw_config))

    column_list = [
        {
            "id": f"{table.name}.{column.name}",
            "name": column.name,
            "type": "",
            "role": column.role,
            "examples": [],
            "description": column.description,
            "alias": column.alias,
            "table_id": table.name,
        }
        for table in meta_config.tables
        for column in table.columns
    ]
    metric_list = [
        {
            "id": metric.name,
            "name": metric.name,
            "description": metric.description,
            "relevant_columns": metric.relevant_columns,
            "alias": metric.alias,
        }
        for metric in meta_config.metrics
    ]

    embedding_client_manager.init()
    embedding_func = embedding_client_manager.client.aembed_query
    await _delete_stale_business_points(COLUMN_COLL, [row["id"] for row in column_list])
    await _delete_stale_business_points(METRIC_COLL, [row["id"] for row in metric_list])
    await insert_column_info_list(column_list, embedding_func)
    await insert_metric_info_list(metric_list, embedding_func)




if __name__ == '__main__':
    # 先初始化客户端
    qdrant_client_manager.init()
    try:
        # asyncio.run(run_test())
        #创建collection playload
        asyncio.run(create_collection())
        #插入数据
        asyncio.run(demo())
    finally:
        # 程序结束强制关闭连接
        asyncio.run(qdrant_client_manager.close())
