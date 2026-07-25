# 负责定义合并召回信息的节点

from typing import Dict, List
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState, MetricInfoState, ColumnInfoState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo


async def merge_retrieved_info(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List]:
    """
    合并字段、取值、指标等召回数据，补全关联表、主外键信息，组装为流程状态结构
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 组装后的表信息、指标信息
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "合并召回信息", "status": "running"})

    # 安全读取召回数据
    retrieved_columns = state.get("retrieved_columns", [])
    retrieved_values = state.get("retrieved_values", [])
    retrieved_metrics = state.get("retrieved_metrics", [])

    meta_mysql_repo = runtime.context["meta_mysql_repository"]

    # 字段ID -> 字段实体 映射，全局去重
    col_id_map: Dict[str, ColumnInfo] = {
        col.id: col for col in retrieved_columns
    }

    try:
        # 1. 根据指标关联字段，补充缺失字段
        for metric in retrieved_metrics:
            for col_id in metric.relevant_columns:
                if col_id not in col_id_map:
                    col_info = await meta_mysql_repo.get_column_info_by_id(col_id)
                    if col_info:
                        col_id_map[col_id] = col_info

        # 2. 根据字段取值，补充字段 & 追加示例值
        for val_item in retrieved_values:
            col_id = val_item.column_id
            val_content = val_item.value

            # 字段不存在则查询补充
            if col_id not in col_id_map:
                col_info = await meta_mysql_repo.get_column_info_by_id(col_id)
                if col_info:
                    col_id_map[col_id] = col_info

            # 示例值去重追加
            col = col_id_map[col_id]
            if val_content not in col.examples:
                col.examples.append(val_content)

        # 3. 按表ID分组：表ID -> 字段列表
        table_col_map: Dict[str, List[ColumnInfo]] = {}
        for col in col_id_map.values():
            table_id = col.table_id
            if table_id not in table_col_map:
                table_col_map[table_id] = []
            table_col_map[table_id].append(col)

        # 4. 补充每张表的主外键字段
        for table_id in list(table_col_map.keys()):
            key_cols = await meta_mysql_repo.get_key_columns_by_table_id(table_id)
            exist_col_ids = [c.id for c in table_col_map[table_id]]

            for key_col in key_cols:
                if key_col.id not in exist_col_ids:
                    table_col_map[table_id].append(key_col)

        # 5. 组装 TableInfoState
        table_infos: List[TableInfoState] = []
        for table_id, col_list in table_col_map.items():
            table_entity = await meta_mysql_repo.get_table_info_by_id(table_id)
            if not table_entity:
                continue

            # 转换为状态结构体
            column_states = [
                ColumnInfoState(
                    name=col.name,
                    type=col.type,
                    role=col.role,
                    examples=col.examples,
                    description=col.description,
                    alias=col.alias
                )
                for col in col_list
            ]

            table_state = TableInfoState(
                name=table_entity.name,
                role=table_entity.role,
                description=table_entity.description,
                columns=column_states
            )
            table_infos.append(table_state)

        # 6. 组装 MetricInfoState
        metric_infos: List[MetricInfoState] = [
            MetricInfoState(
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias
            )
            for metric in retrieved_metrics
        ]

        writer({"type": "progress", "step": "合并召回信息", "status": "success"})
        logger.info(
            f"合并完成 | 表名: {[t['name'] for t in table_infos]} | 指标名: {[m['name'] for m in metric_infos]}"
        )

        return {
            "table_infos": table_infos,
            "metric_infos": metric_infos
        }

    except Exception:
        writer({"type": "progress", "step": "合并召回信息", "status": "error"})
        logger.exception("合并召回信息异常")
        raise