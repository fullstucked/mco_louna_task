import os
from typing import cast

from payments.presentation.http.factory import create_app

if __name__ == "__main__":
    import uvicorn

    port = int(cast(str, os.getenv("API_PORT")))
    host = cast(str, os.getenv("API_HOST"))

    uvicorn.run(
        app=create_app(),
        port=port if port else 8000,
        host=host if host else "0.0.0.0",
        reload=False,
        loop="uvloop",
    )

    # FIX ERROR logger.info("app_started", version="1.0.0", pid=os.getpid())
    # logger.error("operation_failed", error_code="E001", retries=3)
