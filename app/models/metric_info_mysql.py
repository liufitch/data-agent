from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetricInfoMySQL(Base):
    __tablename__ = "metric_info"
    __table_args__ = {"comment": "指标信息表"}

    # 指标编码(主键)
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
        comment="指标编码"
    )

    # 指标名称
    name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="指标名称"
    )

    # 指标描述
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="指标描述"
    )

    # 关联字段(JSON结构)
    relevant_columns: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="关联字段"
    )

    # 指标别名(JSON结构)
    alias: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="指标别名"
    )

    # 通用审计字段（与前两张表对齐）
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