# main.py
# Entry point for the SanzGo FastAPI backend.
# Creates the app, connects the database on startup, and defines the base endpoints.
# Run with: uvicorn app.main:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import db
from app.routers import sensor
from app.routers import auth
from app.middleware import jwt_middleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import devices
from app.routers import alerts
from app.routers import wellness
from app.routers import profile
from app.routers import territory

# Create the FastAPI app instance
app = FastAPI(
    title="SanzGo API",
    description="Backend API for the SanzGo health and territory platform",
    version="0.1.0"
)

# Middleware — CORS must be registered AFTER JWT because middleware runs in reverse order (LIFO)
# So CORS runs first, then JWT
app.add_middleware(BaseHTTPMiddleware, dispatch=jwt_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

# Mount routers
app.include_router(sensor.router)
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(wellness.router)
app.include_router(profile.router)
app.include_router(territory.router)

@app.get("/health")
async def health():
    return {"status": "ok", "message": "SanzGo API is running"}

@app.get("/db-test")
async def db_test():
    async with await db.get_connection() as conn:
        version = await conn.fetchval("SELECT version()")
        return {"status": "ok", "database": version}