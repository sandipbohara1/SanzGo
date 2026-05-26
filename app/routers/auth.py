# auth.py
# Handles all authentication endpoints.
# POST /auth/oauth — verifies a Google id_token and issues a SanzGo JWT

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx                            # makes HTTP requests to Google
from jose import jwt                    # creates and verifies JWT tokens
from datetime import datetime, timedelta, timezone
from app import db
from app.config import (
    GOOGLE_CLIENT_ID,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS
)

# Create the router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# --- Request model ---

class OAuthRequest(BaseModel):
    id_token: str       # the token Google gave to the MAUI app



# --- Helper functions ---

async def verify_google_token(id_token: str) -> dict:
    # Sends the token to Google and gets back the user's information
    # Raises an exception if the token is invalid or expired

    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    data = response.json()

    # Make sure this token was issued for our app specifically
    # Prevents tokens from other apps being used to log into SanzGo
    if data.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token was not issued for SanzGo")

    return data

def create_sanzgo_jwt(user_id: int, email: str) -> str:
    # Creates a SanzGo JWT token for the authenticated user
    # The token expires after JWT_EXPIRY_HOURS hours

    expiry = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)

    payload = {
        "sub": str(user_id),    # subject — the user this token belongs to
        "email": email,
        "exp": expiry           # expiry time — jose checks this automatically
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# --- Endpoints ---

@router.post("/oauth")
async def oauth_login(request: OAuthRequest):
    # Verifies a Google id_token and returns a SanzGo JWT
    # Creates a new user account if this is their first login

    # Step 1 — verify the token with Google
    google_data = await verify_google_token(request.id_token)

    # Extract user info from Google's response
    email = google_data.get("email")
    name = google_data.get("name", email)       # fall back to email if no name
    provider_sub = google_data.get("sub")       # Google's unique ID for this user

    if not email or not provider_sub:
        raise HTTPException(status_code=401, detail="Invalid token data from Google")

    async with await db.get_connection() as conn:

        # Step 2 — check if this Google account is already linked to a user
        identity = await conn.fetchrow("""
            SELECT ui.user_id, u.email
            FROM user_identities ui
            JOIN users u ON u.id = ui.user_id
            WHERE ui.provider = 'google' AND ui.provider_sub = $1
        """, provider_sub)

        if identity:
            # Existing user — just update their last seen and return a JWT
            user_id = identity["user_id"]

            await conn.execute(
                "UPDATE users SET last_seen = NOW() WHERE id = $1",
                user_id
            )

        else:
            # New user — create their account and link their Google identity

            # Check if email already exists from a different provider
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", email
            )

            if existing_user:
                user_id = existing_user["id"]
            else:
                # Create a brand new user
                user = await conn.fetchrow("""
                    INSERT INTO users (display_name, email)
                    VALUES ($1, $2)
                    RETURNING id
                """, name, email)
                user_id = user["id"]

            # Link their Google identity to the user account
            await conn.execute("""
                INSERT INTO user_identities (user_id, provider, provider_sub)
                VALUES ($1, 'google', $2)
            """, user_id, provider_sub)

    # Step 3 — issue a SanzGo JWT
    token = create_sanzgo_jwt(user_id, email)

    return {
        "status": "ok",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": email,
        "display_name": name
    }