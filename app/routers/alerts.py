# alerts.py
# Handles health alert generation and retrieval.
# Alert engine checks every incoming sensor reading against health thresholds.
# GET /alerts/current/{device_id} — returns active unresolved alerts
# GET /alerts/history/{device_id} — returns full alert history

from fastapi import APIRouter, HTTPException, Request
from app import db

# Create the router
router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


# --- Alert thresholds ---
# These define when a sensor reading triggers an alert
# Each metric has a warning level and a critical level

THRESHOLDS = {
    "heart_rate": {
        "high_critical":    130,    # bpm
        "high_warning":     100,    # bpm
        "low_warning":      50,     # bpm
        "low_critical":     40,     # bpm
    },
    "spo2": {
        "low_warning":      95,     # percent
        "low_critical":     90,     # percent
    },
    "aqi": {
        "high_warning":     100,    # AQI index
        "high_critical":    150,    # AQI index
    }
}


# --- Alert engine ---

async def check_and_create_alerts(conn, device_id: int, user_id: int, reading: dict):
    # Called every time a sensor reading is saved
    # Checks the reading against thresholds and creates alerts if needed
    # Also resolves alerts that are no longer triggered

    alerts_to_create = []

    # Check heart rate
    hr = reading.get("heart_rate")
    if hr is not None:
        if hr > THRESHOLDS["heart_rate"]["high_critical"]:
            alerts_to_create.append({
                "type": "heart_rate",
                "severity": "critical",
                "message": f"Heart rate critically high: {hr} bpm",
                "value": hr,
                "threshold": THRESHOLDS["heart_rate"]["high_critical"]
            })
        elif hr > THRESHOLDS["heart_rate"]["high_warning"]:
            alerts_to_create.append({
                "type": "heart_rate",
                "severity": "warning",
                "message": f"Heart rate elevated: {hr} bpm",
                "value": hr,
                "threshold": THRESHOLDS["heart_rate"]["high_warning"]
            })
        elif hr < THRESHOLDS["heart_rate"]["low_critical"]:
            alerts_to_create.append({
                "type": "heart_rate",
                "severity": "critical",
                "message": f"Heart rate critically low: {hr} bpm",
                "value": hr,
                "threshold": THRESHOLDS["heart_rate"]["low_critical"]
            })
        elif hr < THRESHOLDS["heart_rate"]["low_warning"]:
            alerts_to_create.append({
                "type": "heart_rate",
                "severity": "warning",
                "message": f"Heart rate low: {hr} bpm",
                "value": hr,
                "threshold": THRESHOLDS["heart_rate"]["low_warning"]
            })

    # Check SpO2
    spo2 = reading.get("spo2")
    if spo2 is not None:
        if spo2 < THRESHOLDS["spo2"]["low_critical"]:
            alerts_to_create.append({
                "type": "spo2",
                "severity": "critical",
                "message": f"Blood oxygen critically low: {spo2}%",
                "value": spo2,
                "threshold": THRESHOLDS["spo2"]["low_critical"]
            })
        elif spo2 < THRESHOLDS["spo2"]["low_warning"]:
            alerts_to_create.append({
                "type": "spo2",
                "severity": "warning",
                "message": f"Blood oxygen low: {spo2}%",
                "value": spo2,
                "threshold": THRESHOLDS["spo2"]["low_warning"]
            })

    # Check AQI
    aqi = reading.get("aqi")
    if aqi is not None:
        if aqi > THRESHOLDS["aqi"]["high_critical"]:
            alerts_to_create.append({
                "type": "aqi",
                "severity": "critical",
                "message": f"Air quality critically poor: AQI {aqi}",
                "value": aqi,
                "threshold": THRESHOLDS["aqi"]["high_critical"]
            })
        elif aqi > THRESHOLDS["aqi"]["high_warning"]:
            alerts_to_create.append({
                "type": "aqi",
                "severity": "warning",
                "message": f"Air quality poor: AQI {aqi}",
                "value": aqi,
                "threshold": THRESHOLDS["aqi"]["high_warning"]
            })

    # Save all triggered alerts to the database
    for alert in alerts_to_create:
        # Insert into alerts history
        row = await conn.fetchrow("""
            INSERT INTO alerts (device_id, user_id, alert_type, severity, message, value, threshold)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """,
            device_id,
            user_id,
            alert["type"],
            alert["severity"],
            alert["message"],
            alert["value"],
            alert["threshold"]
        )

        # Insert into current alerts
        await conn.execute("""
            INSERT INTO current_alerts (alert_id, device_id, user_id)
            VALUES ($1, $2, $3)
        """, row["id"], device_id, user_id)


# --- Endpoints ---

@router.get("/current/{device_id}")
async def get_current_alerts(device_id: int, request: Request):
    # Returns all active unresolved alerts for a device
    # These are the alerts shown on the Alerts screen in the app

    user_id = request.state.user_id

    async with await db.get_connection() as conn:

        rows = await conn.fetch("""
            SELECT 
                a.id, a.alert_type, a.severity, 
                a.message, a.value, a.threshold, a.created_at
            FROM current_alerts ca
            JOIN alerts a ON a.id = ca.alert_id
            WHERE ca.device_id = $1 AND ca.user_id = $2
            ORDER BY a.created_at DESC
        """, device_id, user_id)

        return {
            "status": "ok",
            "alerts": [dict(r) for r in rows]
        }


@router.get("/history/{device_id}")
async def get_alert_history(device_id: int, request: Request):
    # Returns the full alert history for a device
    # Includes both resolved and unresolved alerts

    user_id = request.state.user_id

    async with await db.get_connection() as conn:

        rows = await conn.fetch("""
            SELECT 
                id, alert_type, severity, message,
                value, threshold, created_at, resolved_at
            FROM alerts
            WHERE device_id = $1 AND user_id = $2
            ORDER BY created_at DESC
            LIMIT 100
        """, device_id, user_id)

        return {
            "status": "ok",
            "alerts": [dict(r) for r in rows]
        }