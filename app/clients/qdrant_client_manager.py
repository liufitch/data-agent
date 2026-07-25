import asyncio
import random
from typing import Optional

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

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
                    size=vec_size,
                    distance=models.Distance.COSINE
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


if __name__ == '__main__':
    # 先初始化客户端
    qdrant_client_manager.init()
    try:
        asyncio.run(run_test())
    finally:
        # 程序结束强制关闭连接
        asyncio.run(qdrant_client_manager.close())