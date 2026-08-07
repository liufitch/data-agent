from typing import Optional

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self._config = config
        self._client: Optional[OpenAIEmbeddings] = None

    def _get_endpoint_url(self) -> str:
        """拼接向量服务地址"""
        return f"http://{self._config.host}:{self._config.port}"

    def init(self) -> None:
        """初始化嵌入模型客户端，幂等执行"""
        if self._client is not None:
            return

        self._client = OpenAIEmbeddings(
            model=self._config.model,
            openai_api_base=f"{self._get_endpoint_url()}/v1/",
            openai_api_key="dummy",  # 本地TEI不需要密钥，占位即可
            timeout=self._config.timeout,
            chunk_size=4,
            # TEI 必须使用模型自身的 tokenizer。若保持默认值，LangChain
            # 会先用 OpenAI tokenizer 生成 token ID，BGE 收到越界 ID 后会崩溃。
            check_embedding_ctx_length=False,
        )

    # 这是自定义封装类的异步销毁方法，用来主动释放
    # OpenAI SDK http 会话（httpx 底层连接池），关闭同步 / 异步 http 客户端，防止连接泄漏，最后把实例引用置空
    async def close(self) -> None:
        """关闭 OpenAI SDK 底层连接并重置客户端。"""
        if self._client is None:
            return
        #安全取属性，属性不存在返回 None，不会抛 AttributeError
        async_resource = getattr(self._client, "async_client", None)
        async_owner = getattr(async_resource, "_client", None)
        if async_owner is not None:
            await async_owner.close()

        sync_resource = getattr(self._client, "client", None)
        sync_owner = getattr(sync_resource, "_client", None)
        if sync_owner is not None:
            sync_owner.close()

        self._client = None

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
