import asyncio

from payments.presentation.ampq.api.v1.events.fetch import handle_bad_events
from payments.presentation.ampq.factory import run_consumer


async def run_periodically(
    interval: int,
    func,
):
    while True:
        try:
            await func()
        except Exception as e:
            pass

        await asyncio.sleep(interval)


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            run_periodically(
                30,
                handle_bad_events,
            )
        )

        tg.create_task(run_consumer())


if __name__ == "__main__":
    asyncio.run(main())
