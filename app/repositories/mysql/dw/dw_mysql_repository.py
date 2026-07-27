# 负责实现dw数据库的读写操作
from typing import Dict, List, Any,Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.log import logger

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

    async def get_db_info(self) -> Dict[str, Optional[str]]:
        """
        获取数据库版本与方言类型
        :return: 包含 version、dialect 的字典
        """
        try:
            # 查询数据库版本
            result = await self.session.execute(text("SELECT VERSION()"))
            version: Optional[str] = result.scalar()
            # 获取数据库方言名称
            dialect = self.session.get_bind().dialect.name

            return {
                "version": version,
                "dialect": dialect
            }
        except Exception:
            logger.exception("获取数据库信息失败")
            return {
                "version": None,
                "dialect": ""
            }

    async def validate_sql(self, sql: str) -> None:
        """
        通过 EXPLAIN 校验 SQL 语法合法性
        :param sql: 待校验 SQL 语句
        """
        if not sql.strip():
            logger.warning("待校验 SQL 为空，跳过校验")
            return

        try:
            # 执行执行计划分析，校验SQL
            await self.session.execute(text(f"EXPLAIN {sql}"))
        except Exception:
            logger.exception(f"SQL 校验失败，SQL: {sql}")
            raise

    async def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """
        执行 SQL 查询，返回字典格式结果集
        :param sql: 待执行 SQL 语句
        :return: 行数据字典列表
        """
        sql = sql.strip()
        # 前置校验空 SQL
        if not sql:
            logger.warning("执行 SQL 为空，终止查询")
            return []

        try:
            result = await self.session.execute(text(sql))
            return [dict(row) for row in result.mappings().fetchall()]
        except Exception:
            logger.exception(f"执行 SQL 异常，SQL: {sql}")
            raise