from fastapi import FastAPI
from.api.v1.router import api_router
from app.core.config import CRYPTO_LIST, FIAT_LIST, settings
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"status": "ok", "project": settings.PROJECT_NAME}


@app.get("/api/v1/currencies", tags=["currencies"])
def list_currencies() -> dict:
    
    #Expose the global currency lists so frontend/other services can
    #consume a single source of truth. Future modules (wallets, rates,
    #orders) should import FIAT_LIST / CRYPTO_LIST from app.core.config
    #directly rather than duplicating these values.
    return {"fiat": FIAT_LIST, "crypto": CRYPTO_LIST}
