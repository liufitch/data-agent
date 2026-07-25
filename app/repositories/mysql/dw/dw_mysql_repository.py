# 负责实现dw数据库的读写操作
from typing import Dict, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def get_column_types(self, table_name: str) -> Dict[str, str]:
        """
        查询指定表的所有字段名与字段类型
        :param table_name: 数据表名
        :return: {字段名: 字段类型}
        """
        # 表名使用标识符引用，防止关键字/特殊字符报错
        sql = text("SHOW COLUMNS FROM :table_name")
        result = await self.session.execute(sql, {"table_name": table_name})
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(
        self, table_name: str, column_name: str, limit: int
    ) -> List:
        """
        查询指定字段的不重复取值
        :param table_name: 数据表名
        :param column_name: 字段名
        :param limit: 最大返回条数
        :return: 字段取值列表
        """
        sql = text(
            "SELECT DISTINCT :column_name FROM :table_name LIMIT :limit"
        )
        result = await self.session.execute(
            sql,
            {
                "table_name": table_name,
                "column_name": column_name,
                "limit": limit
            }
        )
        return result.scalars().fetchall()