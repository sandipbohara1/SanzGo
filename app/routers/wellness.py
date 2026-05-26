# wellness.py
# Handles wellness summary endpoint.
# GET /wellness/summary/today — returns today's average sensor readings

from fastapi import APIRouter, HTTPException, Request
from app import db

# Create the router
router = APIRouter(
    prefix="/wellness",
    tags=["Wellness"]
)


@router.get("/summary/today")
async def get_wellness_summary(request: Request):
    # Returns today's average sensor readings for the logged in user
    # Used by the Wellness screen to show daily health summary

    user_id = request.state.user_id

    async with await db.get_connection() as conn:

        # Find the user's active device
        device = await conn.fetchrow("""
            SELECT id FROM devices
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """, user_id)

        if not device:
            raise HTTPException(
                status_code=404,
                detail="No active device found. Please pair a device first."
            )

        # Get today's average sensor readings for this device
        averages = await conn.fetchrow("""
            SELECT
                AVG(heart_rate)     AS avg_heart_rate,
                AVG(spo2)           AS avg_spo2,
                AVG(temperature)    AS avg_temperature,
                AVG(humidity)       AS avg_humidity,
                AVG(aqi)            AS avg_aqi,
                AVG(eco2)           AS avg_eco2,
                AVG(tvoc)           AS avg_tvoc,
                COUNT(*)            AS total_readings
            FROM sensor_readings
            WHERE device_id = $1
            AND recorded_at >= CURRENT_DATE
            AND recorded_at < CURRENT_DATE + INTERVAL '1 day'
        """, device["id"])

        # No readings today
        if not averages or averages["total_readings"] == 0:
            return {
                "status": "ok",
                "date": "today",
                "total_readings": 0,
                "message": "No sensor readings yet today",
                "averages": {}
            }

        return {
            "status": "ok",
            "date": "today",
            "total_readings": averages["total_readings"],
            "averages": {
                "heart_rate":   round(averages["avg_heart_rate"], 1) if averages["avg_heart_rate"] else None,
                "spo2":         round(averages["avg_spo2"], 1) if averages["avg_spo2"] else None,
                "temperature":  round(averages["avg_temperature"], 1) if averages["avg_temperature"] else None,
                "humidity":     round(averages["avg_humidity"], 1) if averages["avg_humidity"] else None,
                "aqi":          round(averages["avg_aqi"], 1) if averages["avg_aqi"] else None,
                "eco2":         round(averages["avg_eco2"], 1) if averages["avg_eco2"] else None,
                "tvoc":         round(averages["avg_tvoc"], 1) if averages["avg_tvoc"] else None,
            }
        }