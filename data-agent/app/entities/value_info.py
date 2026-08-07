# 用于定义字段取值的业务实体类

from dataclasses import dataclass

@dataclass
class ValueInfo:
    # 单条取值唯一ID
    id: str
    # 字段具体取值
    value: str
    # 关联 ColumnInfo.id
    column_id: str