# 用于定义指标信息的业务实体类
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MetricInfo:
    # 全局唯一ID
    id: str
    # 指标名称
    name: str
    # 指标业务描述与计算口径
    description: Optional[str] = field(default="")
    # 关联字段列表，格式：表名.字段名
    relevant_columns: List[str] = field(default_factory=list)
    # 指标别名/同义词
    alias: List[str] = field(default_factory=list)