from payments.domain.enums.status import PaymentStatus
from payments.domain.enums.currency import Currency
from payments.infrastructure.database.session import metadata
from sqlalchemy import Index
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    Enum,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

payments = Table(
    "payments",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("amount", Numeric(18, 2), nullable=False),
    Column("currency", Enum(Currency, name="currency_enum"), nullable=False),
    Column("description", String, nullable=False),
    Column("metadata", JSON, nullable=False),
    Column(
        "status",
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
    ),
    Column("idempotency_key", UUID(as_uuid=True), nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("processed_at", TIMESTAMP(timezone=True)),
    Column("webhook_url", String, nullable=False),
    Index("ix_payments_idempotency_key", "idempotency_key"),
    Index("ix_payments_payment_id", "id"),
    UniqueConstraint("id", name="uq_payments_id"),
    UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
)
