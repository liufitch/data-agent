import asyncio
from typing import Optional, Dict, Any, List,cast,AsyncGenerator
from elasticsearch import AsyncElasticsearch,  BadRequestError, ApiError
from elasticsearch.helpers import async_streaming_bulk
from sqlalchemy import text

from app.clients import mysql_client_manager
from app.conf.app_config import ESConfig, app_config
import hashlib

class ESClientManager:
    def __init__(self, es_config: ESConfig):
        self._config = es_config
        self._client: Optional[AsyncElasticsearch] = None

    def _get_url(self) -> str:
        return f"http://{self._config.host}:{self._config.port}"

    def init(self) -> None:
        """初始化异步ES客户端，幂等处理"""
        if self._client is not None:
            return
        # 扩展支持账号密码、超时，按需开启
        self._client = AsyncElasticsearch(
            hosts=[self._get_url()],
            basic_auth=(self._config.username, self._config.password)
            if hasattr(self._config, "username") and self._config.username else None,
            request_timeout=getattr(self._config, "timeout", 10)
        )

    async def close(self) -> None:
        """安全关闭连接"""
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> AsyncElasticsearch:
        """安全获取客户端，强制判空"""
        if self._client is None:
            raise RuntimeError("AsyncElasticsearch 未初始化，请先执行 init()")
        return self._client


# 全局单例
es_client_manager = ESClientManager(app_config.es)

# 抽离常量与映射配置，解耦硬编码
INDEX_NAME = "value_info"
VALUE_INFO_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "analysis": {
        "analyzer": {
            "ik_smart_analyzer": {
                "type": "ik_smart"
            }
        }
    }
}
VALUE_INFO_MAPPING: Dict[str, Any] = {
   "properties": {
      "id": {
        "type": "keyword"
      },
      "value": {
        "type": "text",
        "analyzer": "ik_smart_analyzer",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "column_id": {
        "type": "keyword"
      }
    }
}

# 需要采集的维度字段列表 (表名,字段名)
dim_field_list = [
    ("dim_product", "product_name"),
    ("dim_product", "category"),
    ("dim_product", "brand"),
    ("dim_customer", "customer_name"),
    ("dim_customer", "gender"),
    ("dim_customer", "member_level"),
    ("dim_region", "province"),
    ("dim_region", "region_name"),
    ("dim_region", "country"),
    ("dim_date", "quarter"),
    ("dim_date", "month"),
    ("dim_date", "day")
]

sql_parts = []
for table, field in dim_field_list:
    part = f"""
SELECT DISTINCT
    '{table}' AS dim_table,
    '{field}' AS dim_field,
    `{field}` AS field_value
FROM {table}
WHERE `{field}` IS NOT NULL
    """
    sql_parts.append(part.strip())

final_sql = "\nUNION ALL\n".join(sql_parts)

BATCH_FETCH_SIZE = 1000  # mysql每次预加载条数


async def generate_es_bulk_actions() -> AsyncGenerator[dict, None]:
    sql = text(final_sql)
    # 分批读取，读完一批立刻释放mysql连接，不持有长连接
    offset = 0
    while True:
        page_sql = text(f"{final_sql} LIMIT {offset}, {BATCH_FETCH_SIZE}")
        rows_buffer = []
        async with mysql_client_manager.dw_mysql_client_manager.engine.connect() as conn:
            # 不使用stream！改用all()一次性读完当前分页，游标正常结束
            result = await conn.execute(page_sql)
            rows = result.all()
            if not rows:
                break
            rows_buffer = rows

        # mysql连接已经关闭！安全循环产出文档
        for row in rows_buffer:
            raw_key = f"{row.dim_table}|{row.dim_field}|{row.field_value}"
            doc_id = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
            yield {
                "_index": "data-agent-value",
                "_id": doc_id,
                "_source": {
                    "dim_table": row.dim_table,
                    "dim_field": row.dim_field,
                    "field_value": row.field_value
                }
            }
        offset += BATCH_FETCH_SIZE
async def bulk_import_to_es(batch_size: int = 1000):
    success_count = 0
    errors: List[Dict[str, Any]] = []

    # 异步bulk入口：async_streaming_bulk
    async for ok, item in async_streaming_bulk(
            client=es_client_manager.client,
            actions=generate_es_bulk_actions(),
            chunk_size=batch_size,
            raise_on_error=False
    ):
        if ok:
            success_count += 1
        else:
            errors.append(item)

    print(f"成功写入文档数: {success_count}")
    if errors:
        print(f"失败条目：{len(errors)}")
        slice_errors = cast(List[Dict[str, Any]], errors[:10])
        for err in slice_errors:
            print(err)


if __name__ == '__main__':
    mysql_client_manager.dw_mysql_client_manager.init()
    es_client_manager.init()
    try:
        asyncio.run(bulk_import_to_es())
    finally:
        # 程序退出强制关闭连接
        asyncio.run(es_client_manager.close())