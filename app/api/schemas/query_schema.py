# 负责定义查询接口请求体结构

from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    """查询请求入参模型"""
    query: str = Field(
        description="用户自然语言查询语句",
        min_length=1,
        max_length=1000,
        examples=["统计去年各地区的销售总额"]
    )