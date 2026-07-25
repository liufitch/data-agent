from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TableInfoMySQL(Base):
    __tablename__ = "table_info"
    __table_args__ = {"comment": "数据表信息配置表"}  # 表整体注释

    # 主键ID
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
        comment="表编号"
    )

    # 表名称 + 普通索引（按名称查询高频）
    name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="表名称"
    )

    # 表类型：fact=事实表，dim=维度表
    role: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="表类型(fact/dim)"
    )

    # 长文本描述
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="表描述"
    )

    # 通用审计字段（推荐所有业务表加上）
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="软删除标记：0未删除 1已删除"
    )
