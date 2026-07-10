from sqlalchemy import JSON, TIMESTAMP, Column, Enum, Index, String, Table
from sqlalchemy.dialects.postgresql import UUID

from payments.infrastructure.database.outbox.task_status import TaskStatus
from payments.infrastructure.database.session import metadata

outbox = Table(
    "outbox",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, unique=True),
    Column("queue", String, nullable=False),
    Column("payload", JSON, nullable=True),
    Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column(
        "status",
        Enum(TaskStatus, name="task_status_enum"),
        nullable=False,
        default=TaskStatus.PENDING,
    ),
    Column("handled_at", TIMESTAMP(timezone=True), nullable=True),
    Index("ix_outbox_status", "status"),
    Index("ix_outbox_handled_at", "handled_at"),
    Index("ix_outbox_status_handled_at", "status", "handled_at"),
)
