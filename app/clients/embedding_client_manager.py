from typing import Optional

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.embeddings import Embeddings

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self._config = config
        self._client: Optional[HuggingFaceEndpointEmbeddings] = None

    def _get_endpoint_url(self) -> str:
        """拼接向量服务地址"""
        return f"http://{self._config.host}:{self._config.port}"

    def init(self) -> None:
        """初始化嵌入模型客户端，幂等执行"""
        if self._client is not None:
            return
        self._client = HuggingFaceEndpointEmbeddings(
            model=self._get_endpoint_url()
        )

    @property
    def client(self) -> HuggingFaceEndpointEmbeddings:
        """安全获取客户端，非空校验"""
        if self._client is None:
            raise RuntimeError("Embedding 客户端未初始化，请先调用 init()")
        return self._client

    @property
    def embedding(self) -> Embeddings:
        """兼容 LangChain 标准 Embeddings 抽象类型"""
        return self.client


# 全局单例
embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == "__main__":
    # 初始化
    embedding_client_manager.init()
    embed_client = embedding_client_manager.client

    # 单文本向量化
    text = "测试文本向量化"
    vec = embed_client.embed_query(text)
    print(f"向量长度: {len(vec)}")

    # 批量文本向量化
    texts = ["文本1", "文本2", "文本3"]
    vec_list = embed_client.embed_documents(texts)
    print(f"批量向量数量: {len(vec_list)}")