import asyncio
import uuid
from typing import Optional, Dict, Any, List,cast
from elasticsearch import AsyncElasticsearch,  BadRequestError, ApiError
from elasticsearch.helpers import async_streaming_bulk
import pandas as pd
from app.conf.app_config import ESConfig, app_config


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




async def es_test_demo():
    client = es_client_manager.client
    try:
        # 1. 索引不存在才创建
        if not await client.indices.exists(index=INDEX_NAME):
            await client.indices.create(index=INDEX_NAME, mappings=VALUE_INFO_MAPPING,settings=VALUE_INFO_SETTINGS,)
            print(f"索引 {INDEX_NAME} 创建成功")
        else:
            print(f"索引 {INDEX_NAME} 已存在，跳过创建")

        # # 2. 构造bulk操作
        # bulk_ops = []
        # for doc in TEST_VALUE:
        #     bulk_ops.append({"index": {"_index": INDEX_NAME}})
        #     bulk_ops.append(doc)
        #
        # # 3. 批量写入并校验结果
        # bulk_resp = await client.bulk(operations=bulk_ops, refresh=True)
        # if bulk_resp.get("errors"):
        #     print("部分数据写入失败", bulk_resp)
        # else:
        #     print("批量数据写入完成")
        #
        # # 4. 全文检索
        # search_resp = await client.search(
        #     index=INDEX_NAME,
        #     query={"match": {"name": "brave"}}
        # )
        # print("\n检索结果：")
        # for hit in search_resp["hits"]["hits"]:
        #     print(f"文档内容: {hit['_source']}, 分数: {hit['_score']}")


    except BadRequestError as e:
        # 400 错误，比如索引已存在、mapping 语法错
        print(f"请求错误: {e.status_code}, {e.message}")

    except ApiError as e:
        # 所有 ES API 错误的基类
        print(f"ES API 错误: {e}")


async def generate_es_bulk_actions() -> iter:
    """遍历维度表，抽取DISTINCT唯一值，生成Bulk写入Action"""
    for table_name, col_name in dim_field_list:
        column_id = f"{table_name}.{col_name}"
        sql = f"""
            SELECT DISTINCT `{col_name}` AS val
            FROM `{table_name}`
            WHERE `{col_name}` IS NOT NULL AND TRIM(`{col_name}`) != ''
        """
        df = pd.read_sql(sql, con=mysql_client_manager.dw_mysql_client_manager.engine)
        for _, row in df.iterrows():
            val = str(row["val"]).strip()
            doc_id = str(uuid.uuid4())
            yield {
                "_index": INDEX_NAME,
                "_id": doc_id,
                "_source": {
                    "id": doc_id,
                    "value": val,
                    "column_id": column_id
                }
            }

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

import mysql_client_manager
if __name__ == '__main__':
    mysql_client_manager.dw_mysql_client_manager.init()
    es_client_manager.init()
    try:
        asyncio.run(bulk_import_to_es())
    finally:
        # 程序退出强制关闭连接
        asyncio.run(es_client_manager.close())