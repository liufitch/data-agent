# 用于定义表格信息的业务实体类


from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TableInfo:
    # 主键ID（UUID 全局唯一）
    id: str
    # 数据表真实名称
    name: str
    # 表类型：dim / fact
    role: str
    # 业务描述
    description: Optional[str] = field(default="")