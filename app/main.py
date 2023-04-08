
from logging.config import dictConfig

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.endpoints.auth.router import router
from app.endpoints.dashboard.router import router_dashboard




app = FastAPI(
    title="Booking Service"
)

app.include_router(router)
app.include_router(router_dashboard)


