from abc import ABC, abstractmethod


class WebhookSender(ABC):
    """
    WebhookSender sends messages to URL
    """

    @abstractmethod
    async def send(
        self,
        url: str,
        payload: dict[str, str],
        timeout: int = 5,
    ) -> None:
        """
        descr 2
        """
        raise NotImplementedError
