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
