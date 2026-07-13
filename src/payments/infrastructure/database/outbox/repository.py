from sqlalchemy import asc
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.interfaces.outbox_repository import PaymentEventRepository
from payments.domain.enums.task_status import TaskStatus
from payments.domain.events import PaymentDomainEvent
from payments.infrastructure.database.outbox.table import outbox
from payments.infrastructure.utils.events.rebuilder import rebuild_event
from payments.infrastructure.utils.events.serializer import serialize_event


class SqlAlchemyOutboxRepository(PaymentEventRepository):
    """
    PostgreSQL implementation of outbox repository
    to change DB replace insert postgres dialtect  with complimentary one
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, events: Iterable[PaymentDomainEvent]) -> None:
        """
        Writes domain event to db
        Batch writes intend to avoid database overhead
        """
        events_list = list(events)  # Convert to list to check length

        if not events_list:
            return  # Don't execute if empty

        serialized = [serialize_event(e) for e in events]

        stmt = (
            insert(outbox)
            .values(serialized)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

    # pyrefly: ignore [bad-override]
    async def mark_processed(self, event_id: UUID, upd_status: TaskStatus) -> None:
        """Mark an event as processed with explicit lock."""

        # Acquire lock and verify existence
        check_stmt = (
            select(outbox.c.id)
            .where(outbox.c.id == event_id)
            .with_for_update(skip_locked=True)  # Blocking lock, not skip_locked
        )

        result = await self.session.execute(check_stmt)
        if result.scalar_one_or_none() is None:
            raise ValueError(f"Event {event_id} not found in outbox")

        #  Update (lock is retained within transaction)
        update_stmt = (
            update(outbox).where(outbox.c.id == event_id).values(status=upd_status)
        )

        await self.session.execute(update_stmt)
        await self.session.flush()

    async def get_pendings(
        self, limit: int = 50, offset: int = 0
    ) -> list[PaymentDomainEvent]:
        """Rebuilds unprocessed PaymentDomain-based events from outbox table"""

        event_stmt = (
            select(outbox)
            .where(outbox.c.status == TaskStatus.PENDING)
            .order_by(asc(outbox.c.occurred_at))  # Oldest first
            .limit(limit)
            .offset(offset)
            .with_for_update(skip_locked=True)
        )

        rows = (await self.session.execute(event_stmt)).mappings().all()

        return [rebuild_event(dict(row.items())) for row in rows]

    async def mark_in_process(self, event_id: UUID) -> bool:
        """
        Retrieve and lock an event for sensitive communication content like
        external things or client notification. Prevents duplicated messages.

        If event is not `PENDING`, returns False.
        Returns True if successfully transitioned to IN_PROCESS.
        """
        now = datetime.now(timezone.utc)

        # Subquery to lock the row if in PENDING state
        # Uses SKIP LOCKED to avoid blocking if row is already locked
        lock_subq = (
            select(outbox.c.id)
            .where(outbox.c.id == event_id)
            .where(outbox.c.status == TaskStatus.PENDING)
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        # Try to acquire lock on the row
        result = await self.session.execute(lock_subq)
        locked_id = result.scalar_one_or_none()

        if locked_id is None:
            # Row either doesn't exist, already processed, or locked by another transaction
            return False

        # Update the locked row
        update_stmt = (
            update(outbox)
            .where(outbox.c.id == event_id)
            .values(status=TaskStatus.IN_PROCESS, handled_at=now)
        )

        await self.session.execute(update_stmt)
        await self.session.flush()

        return True
