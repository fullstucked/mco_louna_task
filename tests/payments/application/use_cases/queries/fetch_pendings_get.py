from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from payments.application.interfaces.event_publisher import PaymentEventBus
from payments.application.interfaces.uow import PaymentUoW
from payments.application.use_cases.queries.pendings import FetchPendingTasks
from payments.domain.events import PaymentCreatedEvent


class TestFetchPendingTasks:
    """Tests for FetchPendingTasks background job."""

    @pytest.mark.asyncio
    async def test_fetch_and_publish_pending_events(self):
        """FetchPendingTasks should fetch pending events and publish them."""
        # Create mock events
        event1 = PaymentCreatedEvent(
            payment_id=uuid4(),
            amount=100.00,
            currency="USD",
            webhook_url="https://example.com/webhook",
        )
        event2 = PaymentCreatedEvent(
            payment_id=uuid4(),
            amount=50.00,
            currency="EUR",
            webhook_url="https://example.com/webhook",
        )
        pending_events = [event1, event2]

        # Mock outbox
        mock_outbox_repo = AsyncMock()
        mock_outbox_repo.get_pendings = AsyncMock(return_value=pending_events)

        # Mock UoW
        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.outbox = mock_outbox_repo

        # Mock event bus
        mock_event_bus = AsyncMock(spec=PaymentEventBus)
        mock_event_bus.publish_payment_events = AsyncMock()

        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)
        await job()

        # Verify outbox was queried for pending events
        mock_outbox_repo.get_pendings.assert_awaited_once()

        # Verify events were published
        mock_event_bus.publish_payment_events.assert_awaited_once()
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) == 2
        assert event1 in published_events
        assert event2 in published_events

    @pytest.mark.asyncio
    async def test_fetch_no_pending_events(self):
        """FetchPendingTasks should not publish if no pending events exist."""
        # Mock outbox returns empty list
        mock_outbox_repo = AsyncMock()
        mock_outbox_repo.get_pendings = AsyncMock(return_value=[])

        # Mock UoW
        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.outbox = mock_outbox_repo

        # Mock event bus
        mock_event_bus = AsyncMock(spec=PaymentEventBus)
        mock_event_bus.publish_payment_events = AsyncMock()

        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)
        await job()

        # Verify outbox was queried
        mock_outbox_repo.get_pendings.assert_awaited_once()

        # Verify publish was NOT called (no events to publish)
        mock_event_bus.publish_payment_events.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetch_pending_tasks_uses_context_manager(self):
        """FetchPendingTasks should properly use UoW context manager."""
        mock_outbox_repo = AsyncMock()
        mock_outbox_repo.get_pendings = AsyncMock(return_value=[])

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.outbox = mock_outbox_repo

        mock_event_bus = AsyncMock(spec=PaymentEventBus)

        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)
        await job()

        # Verify context manager was used
        mock_uow.__aenter__.assert_awaited_once()
        mock_uow.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_pending_tasks_publish_fails(self):
        """FetchPendingTasks should propagate publishing errors."""
        event = PaymentCreatedEvent(
            payment_id=uuid4(),
            amount=100.00,
            currency="USD",
            webhook_url="https://example.com/webhook",
        )

        mock_outbox_repo = AsyncMock()
        mock_outbox_repo.get_pendings = AsyncMock(return_value=[event])

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.outbox = mock_outbox_repo

        # Event bus publishing fails
        mock_event_bus = AsyncMock(spec=PaymentEventBus)
        mock_event_bus.publish_payment_events = AsyncMock(
            side_effect=Exception("Publishing failed")
        )

        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)

        with pytest.raises(Exception, match="Publishing failed"):
            await job()

    @pytest.mark.asyncio
    async def test_fetch_pending_tasks_get_pendings_fails(self):
        """FetchPendingTasks should propagate outbox retrieval errors."""
        mock_outbox_repo = AsyncMock()
        mock_outbox_repo.get_pendings = AsyncMock(
            side_effect=Exception("Outbox query failed")
        )

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.outbox = mock_outbox_repo

        mock_event_bus = AsyncMock(spec=PaymentEventBus)

        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)

        with pytest.raises(Exception, match="Outbox query failed"):
            await job()

    @pytest.mark.asyncio
    async def test_fetch_pending_tasks_single_event(self):
        """FetchPendingTasks should handle single pending event correctly."""
        event = PaymentCreatedEvent(
            payment_id=uuid4(),
            amount=75.50,
            currency="GBP",
            webhook_url="https://api.example.com/webhook",
        )

        mock_outbox_repo = AsyncMock()
        mock_outbox_repo.get_pendings = AsyncMock(return_value=[event])

        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.outbox = mock_outbox_repo

        mock_event_bus = AsyncMock(spec=PaymentEventBus)
        mock_event_bus.publish_payment_events = AsyncMock()

        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)
        await job()

        # Verify exactly one event was published
        mock_event_bus.publish_payment_events.assert_awaited_once()
        published_events = mock_event_bus.publish_payment_events.call_args[0][0]
        assert len(published_events) == 1
        assert published_events[0] == event

    @pytest.mark.asyncio
    async def test_fetch_pending_tasks_dependency_injection(self):
        """FetchPendingTasks should accept UoW and EventBus via constructor."""
        mock_uow = AsyncMock(spec=PaymentUoW)
        mock_event_bus = AsyncMock(spec=PaymentEventBus)

        # Should initialize without errors
        job = FetchPendingTasks(uow=mock_uow, event_bus=mock_event_bus)

        assert job.uow == mock_uow
        assert job.event_bus == mock_event_bus
