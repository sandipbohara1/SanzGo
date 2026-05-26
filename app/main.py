# main.py
# Entry point for the SanzGo FastAPI backend.
# Creates the app, connects the database on startup, and defines the base endpoints.
# Run with: uvicorn app.main:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import db
from app.routers import sensor


# Create the FastAPI app instance
app = FastAPI(
    title="SanzGo API",
    description="Backend API for the SanzGo health and territory platform",
    version="0.1.0"
)

# Allow the MAUI app and local development tools to call the API
# In production this should be locked down to the actual app domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # allow all origins in development
    allow_methods=["*"],    # allow all HTTP methods
    allow_headers=["*"],    # allow all headers
)


@app.on_event("startup")
async def startup():
    # Runs once when the server starts
    # Creates the database connection pool
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    # Runs once when the server shuts down
    # Cleanly closes all database connections
    await db.disconnect()

# Mount routers — each router handles a group of related endpoints
app.include_router(sensor.router)           # /sensor/add, /sensor/latest/{device_id}


@app.get("/health")
async def health():
    # Simple endpoint to confirm the server is running
    # If this responds, FastAPI is up
    return {
        "status": "ok",
        "message": "SanzGo API is running"
    }


@app.get("/db-test")
async def db_test():
    # Confirms the database is connected and reachable
    # Runs a simple query and returns the PostgreSQL version
    async with await db.get_connection() as conn:
        version = await conn.fetchval("SELECT version()")
        return {
            "status": "ok",
            "database": version
        }