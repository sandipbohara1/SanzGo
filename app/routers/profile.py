# profile.py
# Handles user profile endpoints.
# POST /profile/setup — saves colour and display name on first login
# GET /profile — returns the logged in user's profile
# PUT /profile/update — updates display name and city

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app import db

# Create the router
router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)

# Colours users can pick from for their territory zones
ALLOWED_COLORS = [
    "#00B4A0",  # Teal
    "#1A6FBF",  # Ocean Blue
    "#7B2FBF",  # Purple
    "#E8365D",  # Coral
    "#F5A623",  # Amber
    "#2ECC71",  # Green
    "#E91E8C",  # Pink
    "#FF6B35",  # Orange
]


# --- Request models ---

class ProfileSetupRequest(BaseModel):
    zone_color: str             # must be one of ALLOWED_COLORS
    display_name: Optional[str] = None  # optional — keep Google name if not provided


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    city: Optional[str] = None
    zone_color: Optional[str] = None


# --- Endpoints ---

@router.post("/setup")
async def profile_setup(request: Request, body: ProfileSetupRequest):
    # Called once after first login when user picks their zone colour
    # Also lets them update their display name at the same time

    user_id = request.state.user_id

    # Validate the colour is from our allowed palette
    if body.zone_color not in ALLOWED_COLORS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid colour. Choose from: {ALLOWED_COLORS}"
        )

    async with await db.get_connection() as conn:

        # Check if this colour is already taken by another user
        taken = await conn.fetchrow(
            "SELECT id FROM users WHERE zone_color = $1 AND id != $2",
            body.zone_color, user_id
        )

        if taken:
            raise HTTPException(
                status_code=409,
                detail="This colour is already taken by another player. Please choose a different one."
            )

        # Update the user's zone colour and optionally their display name
        if body.display_name:
            await conn.execute("""
                UPDATE users 
                SET zone_color = $1, display_name = $2
                WHERE id = $3
            """, body.zone_color, body.display_name, user_id)
        else:
            await conn.execute(
                "UPDATE users SET zone_color = $1 WHERE id = $2",
                body.zone_color, user_id
            )

        # Return the updated profile
        user = await conn.fetchrow(
            "SELECT id, display_name, email, city, zone_color FROM users WHERE id = $1",
            user_id
        )

        return {
            "status": "ok",
            "message": "Profile set up successfully",
            "profile": dict(user)
        }


@router.get("/me")
async def get_profile(request: Request):
    # Returns the logged in user's full profile
    # Used by the Profile screen in the app

    user_id = request.state.user_id

    async with await db.get_connection() as conn:

        user = await conn.fetchrow("""
            SELECT 
                u.id, u.display_name, u.email, u.city, 
                u.zone_color, u.created_at, u.last_seen,
                COUNT(t.id) AS zones_owned
            FROM users u
            LEFT JOIN territory_tiles t ON t.owner_id = u.id
            WHERE u.id = $1
            GROUP BY u.id
        """, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "status": "ok",
            "profile": dict(user)
        }


@router.put("/update")
async def update_profile(request: Request, body: ProfileUpdateRequest):
    # Updates the user's display name, city, or zone colour
    # All fields are optional — only updates what is provided

    user_id = request.state.user_id

    # Validate colour if provided
    if body.zone_color and body.zone_color not in ALLOWED_COLORS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid colour. Choose from: {ALLOWED_COLORS}"
        )

    async with await db.get_connection() as conn:

        # Check colour is not taken by another user
        if body.zone_color:
            taken = await conn.fetchrow(
                "SELECT id FROM users WHERE zone_color = $1 AND id != $2",
                body.zone_color, user_id
            )
            if taken:
                raise HTTPException(
                    status_code=409,
                    detail="This colour is already taken by another player."
                )

        # Build update query dynamically based on what was provided
        updates = []
        values = []
        counter = 1

        if body.display_name:
            updates.append(f"display_name = ${counter}")
            values.append(body.display_name)
            counter += 1

        if body.city:
            updates.append(f"city = ${counter}")
            values.append(body.city)
            counter += 1

        if body.zone_color:
            updates.append(f"zone_color = ${counter}")
            values.append(body.zone_color)
            counter += 1

        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No fields provided to update"
            )

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${counter}"
        await conn.execute(query, *values)

        # Return updated profile
        user = await conn.fetchrow(
            "SELECT id, display_name, email, city, zone_color FROM users WHERE id = $1",
            user_id
        )

        return {
            "status": "ok",
            "message": "Profile updated successfully",
            "profile": dict(user)
        }