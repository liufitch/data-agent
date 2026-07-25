from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnMetricMySQL(Base):
    __tablename__ = "column_metric"
    __table_args__ = {"comment": "列与指标关联中间表"}

    # 列编号（联合主键之一，关联 column_info.id）
    column_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("column_info.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        comment="列编号"
    )

    # 指标编号（联合主键之二，关联 metric_info.id）
    metric_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("metric_info.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        comment="指标编号"
    )

    # 统一审计字段
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