import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from structlog import get_logger

from payments.infrastructure.logger.init import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(
        level=os.getenv("LOG_LEVEL", "DEBUG"),
        env=os.getenv("ENV", "DEV"),
    )
    logger = get_logger()

    broker = RabbitBroker(os.getenv("BROKER_URL"))
    await broker.start()

    app.state.logger = logger
    app.state.broker = broker

    logger.info("startup")

    yield

    logger.info("shutdown")

    await broker.stop()
