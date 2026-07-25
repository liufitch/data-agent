from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnInfoMySQL(Base):
    __tablename__ = "column_info"
    __table_args__ = {"comment": "数据表列信息配置表"}

    # 列编号（主键）
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
        comment="列编号"
    )

    # 列名称
    name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="列名称"
    )

    # 数据类型
    type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="数据类型"
    )

    # 列角色：primary_key/foreign_key/measure/dimension
    role: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="列类型(primary_key,foreign_key,measure,dimension)"
    )

    # 数据示例（JSON结构，支持字典/数组）
    examples: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="数据示例"
    )

    # 列别名（JSON结构）
    alias: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="列别名"
    )

    # 关联表ID（外键 + 普通索引，关联 table_info 表）
    table_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("table_info.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="所属表编号"
    )

    # 通用审计字段（与主表保持一致）
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