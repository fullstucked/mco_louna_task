import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger = structlog.get_logger()

    app.state.logger = logger

    broker = RabbitBroker(os.getenv("BROKER_URL"))
    await broker.start()

    app.state.broker = broker

    # logger.info("startup")

    yield

    # logger.info("shutdown")

    await broker.stop()
