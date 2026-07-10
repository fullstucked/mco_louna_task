from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractUnitOfWork(ABC):
    """
    Base class for async Unit of work pattern implementation
    suppoorts autocommit but I prefer explict control over app
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self.rollback()
        else:
            # to autocommit uncomment next line, but I prefer explict
            # await self.commit()
            pass

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError
