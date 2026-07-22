#Python 异步运行时
import asyncio
from typing import Optional

from sqlalchemy import text
#SQLAlchemy 异步引擎 / 会话工厂
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker

from app.conf.app_config import DBConfig, app_config

#基于 SQLAlchemy 异步 + asyncmy 实现的 MySQL 异步客户端管理类
class MysqlClientManager:
     #初始化 & 成员变量 接收单库配置实体，预留异步引擎、会话工厂两个核心实例。
    def __init__(self, db_config: DBConfig):
        self.db_config = db_config
        self.engine: Optional[AsyncEngine] = None
        self.session_factory = None

    def _get_url(self):
        #MySQL 异步驱动（连接串中 mysql+asyncmy 对应此驱动）
        return f"mysql+asyncmy://{self.db_config.user}:{self.db_config.password}@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}?charset=utf8mb4"

    def init(self):
        # 创建异步引擎 + 连接池
        self.engine = create_async_engine(
            url=self._get_url(),
            pool_size=10,  # 连接池常驻连接数
            pool_pre_ping=True , # 执行SQL前探活，防止长连接断开
            max_overflow = 20,  # 连接池最大溢出连接数
            pool_recycle = 3600  # 1小时强制回收连接，适配MySQL默认8小时断连策略
        )
        # 创建异步会话工厂
        self.session_factory = async_sessionmaker(
            self.engine,
            autoflush=True,
            expire_on_commit=False,  # 提交后实例不失效，可继续使用
            autobegin=True  # 自动开启事务
        )

    async def close(self):
        await self.engine.dispose()

dw_mysql_client_manager = MysqlClientManager(app_config.db_dw)
meta_mysql_client_manager = MysqlClientManager(app_config.db_meta)

if __name__ == '__main__':
    meta_mysql_client_manager.init()

    async def test():
        # 异步上下文管理会话，自动关闭会话
        try:
            async with meta_mysql_client_manager.session_factory() as session:
                result = await session.execute(text("select * from table_info limit 10"))
                rows = result.fetchall()
                print(rows)
        except Exception as e:
            print(f"数据库查询异常: {e}")

    asyncio.run(test())