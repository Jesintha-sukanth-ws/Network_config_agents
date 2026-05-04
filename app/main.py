from fastapi import FastAPI
from app.routes.sr_handler import router

app = FastAPI()

app.include_router(router)
