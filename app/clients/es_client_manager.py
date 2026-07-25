import asyncio
from typing import Optional, Dict, Any

from elasticsearch import AsyncElasticsearch, exceptions

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
INDEX_NAME = "my-books"
BOOKS_MAPPING: Dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "name": {"type": "text"},
        "author": {"type": "text"},
        "release_date": {"type": "date", "format": "yyyy-MM-dd"},
        "page_count": {"type": "integer"}
    }
}

# 测试数据
TEST_BOOKS = [
    {"name": "Revelation Space", "author": "Alastair Reynolds", "release_date": "2000-03-15", "page_count": 585},
    {"name": "1984", "author": "George Orwell", "release_date": "1985-06-01", "page_count": 328},
    {"name": "Fahrenheit 451", "author": "Ray Bradbury", "release_date": "1953-10-15", "page_count": 227},
    {"name": "Brave New World", "author": "Aldous Huxley", "release_date": "1932-06-01", "page_count": 268},
    {"name": "The Handmaids Tale", "author": "Margaret Atwood", "release_date": "1985-06-01", "page_count": 311},
]


async def es_test_demo():
    client = es_client_manager.client
    try:
        # 1. 索引不存在才创建
        if not await client.indices.exists(index=INDEX_NAME):
            await client.indices.create(index=INDEX_NAME, mappings=BOOKS_MAPPING)
            print(f"索引 {INDEX_NAME} 创建成功")
        else:
            print(f"索引 {INDEX_NAME} 已存在，跳过创建")

        # 2. 构造bulk操作
        bulk_ops = []
        for doc in TEST_BOOKS:
            bulk_ops.append({"index": {"_index": INDEX_NAME}})
            bulk_ops.append(doc)

        # 3. 批量写入并校验结果
        bulk_resp = await client.bulk(operations=bulk_ops, refresh=True)
        if bulk_resp.get("errors"):
            print("部分数据写入失败", bulk_resp)
        else:
            print("批量数据写入完成")

        # 4. 全文检索
        search_resp = await client.search(
            index=INDEX_NAME,
            query={"match": {"name": "brave"}}
        )
        print("\n检索结果：")
        for hit in search_resp["hits"]["hits"]:
            print(f"文档内容: {hit['_source']}, 分数: {hit['_score']}")

    except exceptions.ElasticsearchException as e:
        print(f"ES 服务异常: {str(e)}")
    except Exception as e:
        print(f"执行异常: {str(e)}")


if __name__ == '__main__':
    es_client_manager.init()
    try:
        asyncio.run(es_test_demo())
    finally:
        # 程序退出强制关闭连接
        asyncio.run(es_client_manager.close())