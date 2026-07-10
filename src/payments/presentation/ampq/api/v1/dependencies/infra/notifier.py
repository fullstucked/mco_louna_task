from payments.infrastructure.notifications.httpx_sender import HttpxWebhookSender


def get_webhook_sender():
    return HttpxWebhookSender()
