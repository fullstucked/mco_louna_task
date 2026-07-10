import os

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

api_key = APIKeyHeader(name="X-API-Key")


api_key_header = APIKeyHeader(name="X-API-Key")


async def get_api_key(
    key: str = Depends(api_key_header),
):
    if key != os.getenv("API_KEY", "dev-key"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return key
