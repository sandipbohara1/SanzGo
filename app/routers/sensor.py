# sensor.py
# Handles all sensor data endpoints.
# POST /sensor/add — receives readings from the Raspberry Pi Pico
# GET /sensor/latest/{device_id} — returns the most recent reading for a device

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel          # validates incoming JSON data
from typing import Optional             # allows nullable fields
from app import db                      # database connection pool


# Create the router — main.py will mount this
router = APIRouter(
    prefix="/sensor",                   # all endpoints start with /sensor
    tags=["Sensor"]                     # groups endpoints in the API docs
)


# --- Request model ---
# Defines exactly what JSON the Pico must send to POST /sensor/add
# Optional fields mean the sensor can send partial data if one sensor fails

class SensorReading(BaseModel):
    api_key: str                        # identifies which device is sending
    heart_rate: Optional[float] = None  # beats per minute from MAX30102
    spo2: Optional[float] = None        # blood oxygen % from MAX30102
    temperature: Optional[float] = None # celsius from AHT21
    humidity: Optional[float] = None    # percentage from AHT21
    aqi: Optional[int] = None           # air quality index from ENS160
    eco2: Optional[int] = None          # equivalent CO2 ppm from ENS160
    tvoc: Optional[int] = None          # total VOC ppb from ENS160


# --- Endpoints ---

@router.post("/add")
async def add_sensor_reading(reading: SensorReading):
    # Receives a sensor reading from the Pico and saves it to the database
    # No JWT required — identified by api_key instead

    async with await db.get_connection() as conn:

        # Look up the device by api_key to get its ID
        device = await conn.fetchrow(
            "SELECT id, user_id, is_active FROM devices WHERE api_key = $1",
            reading.api_key
        )

        # Reject if api_key is not recognised
        if not device:
            raise HTTPException(status_code=401, detail="Invalid api_key")

        # Reject if device has been deactivated
        if not device["is_active"]:
            raise HTTPException(status_code=403, detail="Device is inactive")

        # Save the reading to the database
        row = await conn.fetchrow("""
            INSERT INTO sensor_readings (
                device_id, heart_rate, spo2, temperature,
                humidity, aqi, eco2, tvoc
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, recorded_at
        """,
            device["id"],
            reading.heart_rate,
            reading.spo2,
            reading.temperature,
            reading.humidity,
            reading.aqi,
            reading.eco2,
            reading.tvoc
        )

        # Update the device last_ping timestamp
        await conn.execute(
            "UPDATE devices SET last_ping = NOW() WHERE id = $1",
            device["id"]
        )

        return {
            "status": "ok",
            "reading_id": row["id"],
            "recorded_at": row["recorded_at"]
        }


@router.get("/latest/{device_id}")
async def get_latest_reading(device_id: int):
    # Returns the most recent sensor reading for a given device
    # Used by the dashboard to display current health metrics

    async with await db.get_connection() as conn:

        row = await conn.fetchrow("""
            SELECT 
                id, device_id, recorded_at,
                heart_rate, spo2, temperature,
                humidity, aqi, eco2, tvoc
            FROM sensor_readings
            WHERE device_id = $1
            ORDER BY recorded_at DESC
            LIMIT 1
        """, device_id)

        # Return 404 if no readings exist for this device yet
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No readings found for device {device_id}"
            )

        return {
            "status": "ok",
            "reading": dict(row)
        }