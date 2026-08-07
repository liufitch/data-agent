# 负责实现构建元数据知识库的核心逻辑

import uuid
from typing import List, Dict, Any
from pathlib import Path
from dataclasses import asdict

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

# 全局常量（统一管理魔法值）
EMBEDDING_BATCH_SIZE = 10
COLUMN_SAMPLE_VALUES_LIMIT = 10
COLUMN_FULL_VALUES_LIMIT = 100000


class MetaKnowledgeService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
        value_es_repository: ValueESRepository,
        metric_qdrant_repository: MetricQdrantRepository,
    ):
        self.meta_mysql_repo = meta_mysql_repository
        self.dw_mysql_repo = dw_mysql_repository
        self.col_qdrant_repo = column_qdrant_repository
        self.embed_client = embedding_client
        self.es_value_repo = value_es_repository
        self.metric_qdrant_repo = metric_qdrant_repository

    @staticmethod
    def _gen_unique_id() -> str:
        """生成全局唯一ID，替代名称做主键"""
        return str(uuid.uuid4())

    async def _batch_embedding(
        self, text_list: List[str], batch_size: int
    ) -> List[List[float]]:
        """公共批量向量化方法，复用逻辑"""
        all_embeddings: List[List[float]] = []
        total = len(text_list)
        logger.info(f"开始批量向量化，文本总数: {total}, 批次大小: {batch_size}")

        for idx in range(0, total, batch_size):
            batch_texts = text_list[idx: idx + batch_size]
            try:
                batch_vec = await self.embed_client.aembed_documents(batch_texts)
                all_embeddings.extend(batch_vec)
            except Exception as e:
                logger.exception(f"第 {idx // batch_size + 1} 批向量化失败")
                raise
        return all_embeddings

    async def _save_tables_to_meta_db(self, meta_config: MetaConfig) -> List[ColumnInfo]:
        table_infos: List[TableInfo] = []
        column_infos: List[ColumnInfo] = []
        column_sync_map: Dict[str, bool] = {}

        # 1. 批量查询所有表字段类型，减少DW库查询次数
        all_table_names = [tb.name for tb in meta_config.tables]
        all_column_types: Dict[str, Dict[str, str]] = {}
        for tb_name in all_table_names:
            all_column_types[tb_name] = await self.dw_mysql_repo.get_column_types(tb_name)

        # 2. 遍历构造表、字段实体
        for table in meta_config.tables:
            table_id = self._gen_unique_id()
            table_info = TableInfo(
                id=table_id,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)

            tb_col_types = all_column_types.get(table.name, {})
            for column in table.columns:
                col_key = f"{table.name}.{column.name}"
                column_sync_map[col_key] = column.sync
                col_id = self._gen_unique_id()

                # 获取字段示例值
                col_values = await self.dw_mysql_repo.get_column_values(
                    table.name, column.name, COLUMN_SAMPLE_VALUES_LIMIT
                )
                col_type = tb_col_types.get(column.name, "")

                column_info = ColumnInfo(
                    id=col_id,
                    name=column.name,
                    type=col_type,
                    role=column.role,
                    examples=col_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table_id,
                )
                column_infos.append(column_info)

        # 3. 事务批量入库
        try:
            async with self.meta_mysql_repo.session.begin():
                await self.meta_mysql_repo.save_table_infos(table_infos)
                await self.meta_mysql_repo.save_column_infos(column_infos)
            logger.info(f"成功入库 {len(table_infos)} 张表, {len(column_infos)} 个字段")
        except Exception as e:
            logger.exception("表/字段元数据入库失败")
            raise

        # 挂载同步标记，供后续ES使用
        for col_info in column_infos:
            col_info.sync = column_sync_map.get(f"{col_info.table_id}.{col_info.name}", False)

        return column_infos

    async def _save_column_info_to_qdrant(self, column_infos: List[ColumnInfo]):
        await self.col_qdrant_repo.ensure_collection()
        points: List[Dict[str, Any]] = []

        for col in column_infos:
            # 字段名称、描述、所有别名 分别向量化
            text_items = [col.name, col.description] + col.alias
            for text in text_items:
                if not text:
                    continue
                points.append({
                    "id": self._gen_unique_id(),
                    "embedding_text": text,
                    "payload": asdict(col)
                })

        if not points:
            logger.warning("无有效字段文本，跳过字段向量入库")
            return

        # 批量向量化 + 入库
        texts = [p["embedding_text"] for p in points]
        ids = [str(p["id"]) for p in points]
        payloads = [p["payload"] for p in points]
        embeddings = await self._batch_embedding(texts, EMBEDDING_BATCH_SIZE)

        await self.col_qdrant_repo.upsert(ids, embeddings, payloads)
        logger.info(f"字段向量数据入库Qdrant完成，总数: {len(points)}")

    async def _save_value_info_to_es(
        self, meta_config: MetaConfig, column_infos: List[ColumnInfo]
    ):
        await self.es_value_repo.ensure_index()
        value_infos: List[ValueInfo] = []

        for col_info in column_infos:
            if not getattr(col_info, "sync", False):
                continue

            tb_name = col_info.table_id
            col_name = col_info.name
            try:
                values = await self.dw_mysql_repo.get_column_values(
                    tb_name, col_name, COLUMN_FULL_VALUES_LIMIT
                )
            except Exception as e:
                logger.warning(f"获取字段 {tb_name}.{col_name} 取值失败: {e}")
                continue

            for val in values:
                val_id = self._gen_unique_id()
                value_infos.append(ValueInfo(
                    id=val_id,
                    value=val,
                    column_id=col_info.id
                ))

        if not value_infos:
            logger.info("无需要同步至ES的字段取值，跳过ES入库")
            return

        await self.es_value_repo.index(value_infos)
        logger.info(f"字段取值入库ES完成，总数: {len(value_infos)}")

    async def _save_metrics_to_meta_db(self, meta_config: MetaConfig) -> List[MetricInfo]:
        metric_infos: List[MetricInfo] = []
        column_metrics: List[ColumnMetric] = []

        for metric in meta_config.metrics:
            metric_id = self._gen_unique_id()
            metric_info = MetricInfo(
                id=metric_id,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info)

            for rel_col in metric.relevant_columns:
                column_metrics.append(ColumnMetric(
                    column_id=rel_col,
                    metric_id=metric_id
                ))

        try:
            async with self.meta_mysql_repo.session.begin():
                await self.meta_mysql_repo.save_metric_infos(metric_infos)
                await self.meta_mysql_repo.save_column_metrics(column_metrics)
            logger.info(f"成功入库 {len(metric_infos)} 个指标, {len(column_metrics)} 条关联关系")
        except Exception as e:
            logger.exception("指标/字段关联数据入库失败")
            raise

        return metric_infos

    async def _save_metric_info_to_qdrant(self, metric_infos: List[MetricInfo]):
        await self.metric_qdrant_repo.ensure_collection()
        points: List[Dict[str, Any]] = []

        for metric in metric_infos:
            text_items = [metric.name, metric.description] + metric.alias
            for text in text_items:
                if not text:
                    continue
                points.append({
                    "id": self._gen_unique_id(),
                    "embedding_text": text,
                    "payload": asdict(metric)
                })

        if not points:
            logger.warning("无有效指标文本，跳过指标向量入库")
            return

        texts = [p["embedding_text"] for p in points]
        ids = [str(p["id"]) for p in points]
        payloads = [p["payload"] for p in points]
        embeddings = await self._batch_embedding(texts, EMBEDDING_BATCH_SIZE)

        await self.metric_qdrant_repo.upsert(ids, embeddings, payloads)
        logger.info(f"指标向量数据入库Qdrant完成，总数: {len(points)}")

    async def build(self, config_path: Path):
        """主构建入口：加载配置 -> 全流程构建元知识库"""
        logger.info(f"开始加载元数据配置文件: {config_path}")
        try:
            raw_conf: ConfigDict = OmegaConf.load(config_path)
            schema = OmegaConf.structured(MetaConfig)
            meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, raw_conf))
        except Exception as e:
            logger.exception("配置文件加载/解析失败")
            return

        # 处理表、字段全流程
        if meta_config.tables:
            column_infos = await self._save_tables_to_meta_db(meta_config)
            await self._save_column_info_to_qdrant(column_infos)
            await self._save_value_info_to_es(meta_config, column_infos)

        # 处理指标全流程
        if meta_config.metrics:
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            await self._save_metric_info_to_qdrant(metric_infos)

        logger.info("===== 元知识库全量构建完成 =====")