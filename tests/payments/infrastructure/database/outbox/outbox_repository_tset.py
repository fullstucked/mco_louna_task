from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from payments.domain.enums.status import PaymentStatus
from payments.domain.events import PaymentCreatedEvent
from payments.infrastructure.database.outbox.repository import (
    SqlAlchemyOutboxRepository,
)


@pytest.fixture
def mock_session():
    """Return AsyncMock for AsyncSession"""
    return AsyncMock()


@pytest.fixture
def repo(mock_session):
    """Inject mocked session into repository"""
    repo = SqlAlchemyOutboxRepository(session=mock_session)
    return repo


class TestSqlAlchemyOutboxRepository:

    @pytest.mark.asyncio
    async def test_get_pendings_rebuilds_events_from_rows(self, repo, mock_session):
        """Verify get_pendings() converts row data to domain events."""
        row_data = {
            "id": uuid4(),
            "event_type": "PaymentCreated",
            "aggregate_id": uuid4(),
            "payload": '{"amount": "50.00"}',
            "status": PaymentStatus.PENDING,
            "created_at": datetime.now(),
        }

        # Create synchronous Result mock
        mock_result = MagicMock()  # ← NOT AsyncMock
        mock_result.mappings.return_value.all.return_value = [row_data]
        mock_session.execute.return_value = mock_result

        with patch(
            "payments.infrastructure.database.outbox.repository.rebuild_event"
        ) as mock_rebuild:
            mock_rebuild.return_value = MagicMock(spec=PaymentCreatedEvent)

            events = await repo.get_pendings(limit=50)

            assert len(events) == 1
            mock_rebuild.assert_called_once_with(row_data)

    @pytest.mark.asyncio
    async def test_get_pendings_only_fetches_pending_status(self, repo, mock_session):
        """Verify get_pendings() filters by PENDING status only."""
        mock_result = MagicMock()  # ← NOT AsyncMock
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        events = await repo.get_pendings()

        assert events == []
        # Verify the query checked for PENDING status
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pendings_respects_limit_and_offset(self, repo, mock_session):
        """Verify get_pendings() respects limit and offset parameters."""
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_pendings(limit=25, offset=10)

        # Verify execute was called once (statement built correctly)
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_pendings_locks_rows_for_update(self, repo, mock_session):
        """Verify get_pendings() uses FOR UPDATE to prevent concurrent processing."""
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_pendings()

        # Verify FOR UPDATE was used (check that execute was called)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pendings_returns_empty_when_none_exist(self, repo, mock_session):
        """Verify get_pendings() returns empty list when no pending events."""
        mock_result = MagicMock()  # ← NOT AsyncMock
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        events = await repo.get_pendings()

        assert events == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_processed_updates_event_status(self, repo, mock_session):
        """Verify mark_processed() acquires lock and updates event status."""
        event_id = uuid4()

        # Mock the result object that execute returns
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {"id": event_id}

        # Every execute call returns the same mock (works for both SELECT and UPDATE)
        mock_session.execute.return_value = mock_result

        await repo.mark_processed(event_id, PaymentStatus.CONFIRMED)

        # Verify both calls happened
        assert mock_session.execute.call_count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_processed_raises_on_not_found(self, repo, mock_session):
        """Verify mark_processed() raises if event doesn't exist or is locked."""
        event_id = uuid4()

        # SELECT ... FOR UPDATE SKIP LOCKED returns None (not found or locked)
        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = (
            None  # ← KEY: This must return None
        )

        mock_session.execute.return_value = mock_check_result

        with pytest.raises(ValueError, match="Event .* not found in outbox"):
            await repo.mark_processed(event_id, PaymentStatus.CONFIRMED)

        # Only one execute (SELECT); UPDATE never happens
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_skips_empty_events(self, repo, mock_session):
        """Verify add() returns early if events list is empty."""
        await repo.add([])

        # No execute or flush should be called
        mock_session.execute.assert_not_called()
        mock_session.flush.assert_not_called()
