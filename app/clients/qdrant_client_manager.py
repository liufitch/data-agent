import asyncio
import random
import hashlib
from typing import Optional,List
import uuid
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance, VectorParams,PointStruct,
    KeywordIndexParams, TextIndexParams, TokenizerType
)
from app.conf.app_config import QdrantConfig, app_config


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
    points = []
    for row in column_list:
        # 组装用于向量化的文本
        alias_str = ",".join(row["alias"]) if isinstance(row["alias"], list) else str(row["alias"])
        examples_str = ",".join([str(x) for x in row["examples"]]) if isinstance(row["examples"], list) else str(row["examples"])
        embed_text = (
            f"列名称：{row['name']}\n"
            f"列类型：{row['type']}\n"
            f"列角色：{row['role']}\n"
            f"列描述：{row['description']}\n"
            f"别名：{alias_str}\n"
            f"示例值：{examples_str}"
        )
        # 获取embedding向量
        vec = await embedding_func(embed_text)
        point = PointStruct(
            id=str(uuid.uuid4()),  # point主键uuid，和业务id分离
            vector=vec,
            payload=row  # payload直接存入原始字典，和截图结构一致
        )
        points.append(point)

    # 批量upsert
    await client.upsert(
        collection_name=COLUMN_COLL,
        points=points
    )
    print(f"✅ 成功写入 {len(points)} 条字段元数据")


async def insert_metric_info_list(metric_list: List[dict], embedding_func):
    """
    批量插入指标元数据
    :param metric_list: 原始metric_info数据库记录列表
    :param embedding_func: 异步embedding函数
    """
    client = qdrant_client_manager.client
    if client is None:
        raise RuntimeError("Qdrant AsyncClient 未初始化，请先调用 init()")
    points = []
    for row in metric_list:
        alias_str = ",".join(row["alias"]) if isinstance(row["alias"], list) else str(row["alias"])
        rel_col_str = ",".join(row["relevant_columns"]) if isinstance(row["relevant_columns"], list) else str(row["relevant_columns"])
        embed_text = (
            f"指标名称：{row['name']}\n"
            f"指标描述：{row['description']}\n"
            f"关联字段：{rel_col_str}\n"
            f"别名：{alias_str}"
        )
        vec = await embedding_func(embed_text)
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload=row
        )
        points.append(point)

    await client.upsert(
        collection_name=METRIC_COLL,
        points=points
    )
    print(f"✅ 成功写入 {len(points)} 条指标元数据")


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


# ===================== 测试Demo=====================
async def demo():
    # 样例 column_info 数据
    sample_columns = [
    {
        "id": "dim_region.region_name",
        "name": "region_name",
        "type": "varchar(50)",
        "role": "dimension",
        "examples": ["华东", "华南", "西南", "华北", "华中"],
        "description": "订单所属的大区名称，如华东、华南等。",
        "alias": ["地区", "区域", "大区"],
        "table_id": "dim_region"
    },
    {
        "id": "fact_order.order_amount",
        "name": "order_amount",
        "type": "decimal(18,2)",
        "role": "measure",
        "examples": [99.90, 199.50, 1299.00],
        "description": "单笔订单的成交金额，单位为元，包含商品金额和运费。",
        "alias": ["订单金额", "成交金额", "支付金额"],
        "table_id": "fact_order"
    },
    {
        "id": "fact_order.order_id",
        "name": "order_id",
        "type": "varchar(32)",
        "role": "primary_key",
        "examples": ["ORD202401010001", "ORD202401010002"],
        "description": "订单唯一标识，系统生成的主键ID。",
        "alias": ["订单号", "订单编号"],
        "table_id": "fact_order"
    },
    {
        "id": "dim_customer.customer_name",
        "name": "customer_name",
        "type": "varchar(100)",
        "role": "dimension",
        "examples": ["张三", "李四", "王五"],
        "description": "客户的真实姓名，用于客户维度分析。",
        "alias": ["客户姓名", "用户名", "客户名"],
        "table_id": "dim_customer"
    },
    {
        "id": "fact_order.create_time",
        "name": "create_time",
        "type": "datetime",
        "role": "time_dimension",
        "examples": ["2024-01-01 10:30:00", "2024-01-15 14:20:00"],
        "description": "订单创建时间，即用户下单的时间戳。",
        "alias": ["下单时间", "创建时间", "订单时间"],
        "table_id": "fact_order"
    }
]

    # 样例 metric_info 数据
    sample_metrics = [
    {
        "id": "GMV",
        "name": "GMV",
        "description": "全称 Gross Merchandise Value，表示所有订单的成交金额总和。",
        "relevant_columns": ["fact_order.order_amount"],
        "alias": ["成交总额", "订单总额", "商品交易总额"]
    },
    {
        "id": "order_count",
        "name": "订单量",
        "description": "统计周期内的有效订单总数量，不含已取消和退款订单。",
        "relevant_columns": ["fact_order.order_id"],
        "alias": ["订单数", "订单总量", "下单量"]
    },
    {
        "id": "customer_count",
        "name": "客户数",
        "description": "统计周期内有下单行为的去重客户总数量。",
        "relevant_columns": ["dim_customer.customer_name"],
        "alias": ["用户数", "客户数量", "下单用户数"]
    },
    {
        "id": "AOV",
        "name": "客单价",
        "description": "Average Order Value，平均每笔订单的成交金额，计算公式：GMV / 订单量。",
        "relevant_columns": ["fact_order.order_amount", "fact_order.order_id"],
        "alias": ["平均客单价", "单均金额", "平均订单金额"]
    }
]

    # ------------------- 这里替换成你真实的 Embedding 异步调用函数 -------------------
    async def mock_embedding(text: str) -> list[float]:
        """临时模拟embedding，上线替换成BGE-Large-Zh服务调用"""
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
        rng = random.Random(seed)
        return [rng.random() for _ in range(VECTOR_DIM)]
    # ----------------------------------------------------------------------------

    await insert_column_info_list(sample_columns, mock_embedding)
    await insert_metric_info_list(sample_metrics, mock_embedding)




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