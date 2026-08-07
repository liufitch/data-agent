# 用于定义字段指标关系的业务实体类

from dataclasses import dataclass

@dataclass
class ColumnMetric:
    # 字段唯一ID，关联 ColumnInfo.id
    column_id: str
    # 指标唯一ID，关联 MetricInfo.id
    metric_id: str