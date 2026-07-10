from payments.application.use_cases.events.notify import SendNotificationUseCase
from payments.application.use_cases.queries.pendings import FetchPendingTasks


def get_notify_uc() -> SendNotificationUseCase:
    return SendNotificationUseCase()


def get_pending_events_uc() -> FetchPendingTasks:
    return FetchPendingTasks()
