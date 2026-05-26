# middleware.py
# JWT authentication middleware for the SanzGo API.
# Checks the Authorization header on every request except whitelisted routes.
# If the token is missing, invalid, or expired the request is rejected with 401.

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from app.config import JWT_SECRET, JWT_ALGORITHM

# Routes that do not require a JWT token
# sensor/add is open because the Pico has no secure storage
WHITELISTED_ROUTES = [
    "/health",
    "/db-test",
    "/auth/oauth",
    "/sensor/add",
    "/docs",
    "/openapi.json",
    "/redoc"
]


async def jwt_middleware(request: Request, call_next):
    # Check if this route is whitelisted — skip auth if it is
    if request.url.path in WHITELISTED_ROUTES:
        return await call_next(request)

    # Get the Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authorization header missing"}
        )

    # Header must be in format: Bearer <token>
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid Authorization header format. Use: Bearer <token>"}
        )

    token = parts[1]

    try:
        # Verify the token signature and expiry
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Attach the user info to the request so endpoints can access it
        request.state.user_id = int(payload["sub"])
        request.state.email = payload["email"]

    except JWTError:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"}
        )

    return await call_next(request)