# 日志配置
from dataclasses import dataclass
from pathlib import Path
# 配置文件加载工具为OmegaConf
from omegaconf import OmegaConf

# 日志
@dataclass
class File: #对应 logging.file
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str

@dataclass
class Console: #对应 logging.console
    enable: bool
    level: str

@dataclass
class LoggingConfig: #聚合日志两大子配置
    file: File
    console: Console

# 数据库配置
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

#对应向量库
@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int

#向量化服务
@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str

@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str

@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str

#顶层入口，聚合所有子配置，是最终使用的总配置类
@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig

config_file = Path(__file__).parents[2] / 'conf' / 'app_config.yaml'
# 1. 读取原始YAML配置
context = OmegaConf.load(config_file)
# 2. 基于数据类生成配置Schema（类型校验模板）
schema = OmegaConf.structured(AppConfig)
# 3. 合并配置 + 强类型转为Python对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))