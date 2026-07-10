import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from structlog import get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = get_logger()

    broker = RabbitBroker(os.getenv("BROKER_URL"))
    await broker.start()

    app.state.logger = logger
    app.state.broker = broker

    logger.info("startup")

    yield

    logger.info("shutdown")

    await broker.stop()
