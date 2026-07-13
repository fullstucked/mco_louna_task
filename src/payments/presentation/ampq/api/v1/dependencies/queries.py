from payments.application.handlers.events.notify import SendNotificationUseCase
from payments.application.handlers.queries.pendings import FetchPendingTasks


def get_notify_uc() -> SendNotificationUseCase:
    return SendNotificationUseCase()


def get_pending_events_uc() -> FetchPendingTasks:
    return FetchPendingTasks()
