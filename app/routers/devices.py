# devices.py
# Handles device pairing and listing endpoints.
# POST /devices/pair — pairs a new Raspberry Pi Pico to the logged in user
# GET /devices/mine — returns all devices belonging to the logged in user

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import secrets                          # generates cryptographically secure api keys
from app import db

# Create the router
router = APIRouter(
    prefix="/devices",
    tags=["Devices"]
)


# --- Request model ---

class PairDeviceRequest(BaseModel):
    device_name: str    # a friendly name for the device e.g. "My Pico"


# --- Endpoints ---

@router.post("/pair")
async def pair_device(request: Request, body: PairDeviceRequest):
    # Creates a new device record linked to the logged in user
    # Generates a unique api_key the user will enter into the Pico firmware
    # Requires JWT — we need to know which user is pairing the device

    # Get the user_id from the JWT — middleware already verified the token
    user_id = request.state.user_id

    # Generate a secure random api_key for this device
    # This is what the Pico will send with every sensor reading
    api_key = secrets.token_hex(32)

    async with await db.get_connection() as conn:

        # Check if this user already has a device with the same name
        existing = await conn.fetchrow("""
            SELECT id FROM devices 
            WHERE user_id = $1 AND device_name = $2
        """, user_id, body.device_name)

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"You already have a device named '{body.device_name}'"
            )

        # Save the new device to the database
        device = await conn.fetchrow("""
            INSERT INTO devices (user_id, device_name, api_key)
            VALUES ($1, $2, $3)
            RETURNING id, device_name, api_key, created_at
        """, user_id, body.device_name, api_key)

        return {
            "status": "ok",
            "device_id": device["id"],
            "device_name": device["device_name"],
            "api_key": device["api_key"],       # user copies this into Pico firmware
            "created_at": device["created_at"],
            "message": "Copy the api_key into your Pico firmware. It will not be shown again."
        }


@router.get("/mine")
async def get_my_devices(request: Request):
    # Returns all devices belonging to the logged in user
    # Used by the app to show which Picos are paired

    user_id = request.state.user_id

    async with await db.get_connection() as conn:

        devices = await conn.fetch("""
            SELECT id, device_name, is_active, created_at, last_ping
            FROM devices
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user_id)

        # Return empty list if no devices paired yet
        return {
            "status": "ok",
            "devices": [dict(d) for d in devices]
        }