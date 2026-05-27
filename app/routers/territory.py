# territory.py
# Handles all territory and run endpoints.
# POST /territory/run/upload — uploads a GPS run, creates or steals zones
# GET /territory/tiles — returns nearby zones as GeoJSON for Mapbox
# GET /territory/leaderboard — returns top users by zones owned

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
from app import db
from datetime import datetime

# Create the router
router = APIRouter(
    prefix="/territory",
    tags=["Territory"]
)

# Minimum loop perimeter in metres to create a valid zone
MIN_PERIMETER_METRES = 100

# How close the end point must be to the start point to close the loop
LOOP_CLOSURE_METRES = 10


# --- Request models ---

class GPSPoint(BaseModel):
    lat: float      # latitude
    lng: float      # longitude
    timestamp: str  # ISO timestamp when point was recorded


class RunUploadRequest(BaseModel):
    points: List[GPSPoint]  # ordered list of GPS points from the run
    started_at: str         # ISO timestamp when run started
    ended_at: str           # ISO timestamp when run ended

# --- Helper functions ---

def points_to_linestring(points: List[GPSPoint]) -> str:
    # Converts a list of GPS points to a PostGIS LineString WKT string
    # Example: LINESTRING(-113.49 53.46, -113.48 53.47, ...)
    coords = ", ".join(f"{p.lng} {p.lat}" for p in points)
    return f"LINESTRING({coords})"


def points_to_polygon(points: List[GPSPoint]) -> str:
    # Converts a list of GPS points to a PostGIS Polygon WKT string
    # First and last point must be the same to close the polygon
    coords = ", ".join(f"{p.lng} {p.lat}" for p in points)
    # Close the polygon by repeating the first point at the end
    first = f"{points[0].lng} {points[0].lat}"
    return f"POLYGON(({coords}, {first}))"


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # Calculates the distance in metres between two GPS coordinates
    # Used to check if the loop is closed and measure perimeter
    import math
    R = 6371000  # Earth radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def calculate_perimeter(points: List[GPSPoint]) -> float:
    # Calculates the total perimeter of the run path in metres
    total = 0
    for i in range(len(points) - 1):
        total += haversine_distance(
            points[i].lat, points[i].lng,
            points[i+1].lat, points[i+1].lng
        )
    return total

# --- Endpoints ---

@router.post("/run/upload")
async def upload_run(request: Request, body: RunUploadRequest):
    # Receives GPS points from a completed run
    # If the path forms a closed loop it creates or steals territory zones
    # If overlapping existing zones, claims only the overlapping portion

    user_id = request.state.user_id

    # Need at least 4 points to form a valid polygon
    if len(body.points) < 4:
        raise HTTPException(
            status_code=400,
            detail="Not enough GPS points to form a zone. Keep running."
        )

    # Check if the loop is closed — end point must be within LOOP_CLOSURE_METRES of start
    closure_distance = haversine_distance(
        body.points[0].lat, body.points[0].lng,
        body.points[-1].lat, body.points[-1].lng
    )

    is_loop = closure_distance <= LOOP_CLOSURE_METRES

    # Calculate total perimeter
    perimeter = calculate_perimeter(body.points)

    # Build the LineString for storing the run path
    linestring = points_to_linestring(body.points)

    async with await db.get_connection() as conn:

        # Save the run to the database regardless of whether it forms a loop
        run = await conn.fetchrow("""
            INSERT INTO runs (user_id, started_at, ended_at, path, distance_metres)
            VALUES ($1, $2, $3, ST_GeomFromText($4, 4326), $5)
            RETURNING id
        """,
            user_id,
            datetime.fromisoformat(body.started_at),
            datetime.fromisoformat(body.ended_at),
            linestring,
            int(perimeter)
        )

        run_id = run["id"]

        # If not a closed loop — just save the run, no zone created
        if not is_loop:
            return {
                "status": "ok",
                "run_id": run_id,
                "is_loop": False,
                "message": f"Run saved. End point was {closure_distance:.0f}m from start — loop not closed. Need within {LOOP_CLOSURE_METRES}m.",
                "distance_metres": int(perimeter)
            }

        # Check minimum perimeter
        if perimeter < MIN_PERIMETER_METRES:
            return {
                "status": "ok",
                "run_id": run_id,
                "is_loop": True,
                "message": f"Loop closed but perimeter {perimeter:.0f}m is too small. Minimum is {MIN_PERIMETER_METRES}m.",
                "distance_metres": int(perimeter)
            }

        # Build the polygon from the GPS points
        polygon = points_to_polygon(body.points)

        # Find all existing zones that overlap with the new polygon
        overlapping = await conn.fetch("""
            SELECT id, owner_id,
                ST_AsGeoJSON(ST_Intersection(boundary, ST_GeomFromText($1, 4326))) AS stolen_portion,
                ST_AsGeoJSON(ST_Difference(boundary, ST_GeomFromText($1, 4326))) AS remaining_portion
            FROM territory_tiles
            WHERE ST_Intersects(boundary, ST_GeomFromText($1, 4326))
            AND owner_id != $2
        """, polygon, user_id)

        stolen_zones = []
        previous_owners = set()

        for zone in overlapping:
            previous_owner_id = zone["owner_id"]
            previous_owners.add(previous_owner_id)

            # Check if remaining portion is valid — not empty or too small
            remaining = await conn.fetchval("""
                SELECT ST_Area(ST_GeomFromGeoJSON($1)::geography)
            """, zone["remaining_portion"])

            if remaining and remaining > 10:
                # Update original zone to only the remaining portion
                await conn.execute("""
                    UPDATE territory_tiles
                    SET boundary = ST_GeomFromGeoJSON($1),
                        claimed_at = NOW()
                    WHERE id = $2
                """, zone["remaining_portion"], zone["id"])

                # Create a new zone for the stolen portion
                new_zone = await conn.fetchrow("""
                    INSERT INTO territory_tiles (boundary, owner_id, claimed_at)
                    VALUES (ST_GeomFromGeoJSON($1), $2, NOW())
                    RETURNING id
                """, zone["stolen_portion"], user_id)

                stolen_zones.append(new_zone["id"])
            else:
                # Remaining portion is too small — transfer entire zone
                await conn.execute("""
                    UPDATE territory_tiles
                    SET owner_id = $1, claimed_at = NOW()
                    WHERE id = $2
                """, user_id, zone["id"])

                stolen_zones.append(zone["id"])

            # Record the steal event
            await conn.execute("""
                INSERT INTO territory_events (tile_id, run_id, new_owner_id, previous_owner_id, event_type)
                VALUES ($1, $2, $3, $4, 'stolen')
            """, zone["id"], run_id, user_id, previous_owner_id)

        # Create the new zone for the area the user ran around
        new_tile = await conn.fetchrow("""
            INSERT INTO territory_tiles (boundary, owner_id, claimed_at)
            VALUES (ST_GeomFromText($1, 4326), $2, NOW())
            RETURNING id
        """, polygon, user_id)

        # Record the claim event
        await conn.execute("""
            INSERT INTO territory_events (tile_id, run_id, new_owner_id, previous_owner_id, event_type)
            VALUES ($1, $2, $3, NULL, 'claimed')
        """, new_tile["id"], run_id, user_id)

        # Send notifications to previous owners whose zones were stolen
        for prev_owner_id in previous_owners:
            await conn.execute("""
                INSERT INTO notifications (user_id, title, body, type)
                VALUES ($1, 'Zone Stolen!', $2, 'territory_stolen')
            """, prev_owner_id,
                f"Someone just claimed part of your territory. Run back to reclaim it!")

        return {
            "status": "ok",
            "run_id": run_id,
            "is_loop": True,
            "zone_created": new_tile["id"],
            "zones_affected": len(stolen_zones),
            "distance_metres": int(perimeter),
            "message": f"Zone created successfully. {len(stolen_zones)} zones affected."
        }
    
@router.get("/tiles")
async def get_territory_tiles(request: Request, lat: float, lng: float, radius: float = 500):
    # Returns all territory zones within radius metres of the given coordinates
    # Used by Mapbox to render zone overlays on the map
    # Returns GeoJSON FeatureCollection — Mapbox reads this directly

    async with await db.get_connection() as conn:

        tiles = await conn.fetch("""
            SELECT
                t.id,
                t.owner_id,
                t.claimed_at,
                u.display_name AS owner_name,
                u.zone_color AS owner_color,
                ST_AsGeoJSON(t.boundary) AS geometry
            FROM territory_tiles t
            LEFT JOIN users u ON u.id = t.owner_id
            WHERE ST_DWithin(
                t.boundary::geography,
                ST_MakePoint($1, $2)::geography,
                $3
            )
        """, lng, lat, radius)

        # Build GeoJSON FeatureCollection
        # Mapbox expects this exact format for rendering overlays
        features = []
        for tile in tiles:
            features.append({
                "type": "Feature",
                "geometry": tile["geometry"],
                "properties": {
                    "tile_id": tile["id"],
                    "owner_id": tile["owner_id"],
                    "owner_name": tile["owner_name"],
                    "owner_color": tile["owner_color"] or "#FFFFFF",
                    "claimed_at": str(tile["claimed_at"]) if tile["claimed_at"] else None
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }


@router.get("/leaderboard")
async def get_leaderboard(request: Request):
    # Returns top 10 users by number of territory zones owned
    # Used by the leaderboard panel on the Territory screen

    async with await db.get_connection() as conn:

        rows = await conn.fetch("""
            SELECT
                u.id,
                u.display_name,
                u.zone_color,
                COUNT(t.id) AS zones_owned
            FROM users u
            LEFT JOIN territory_tiles t ON t.owner_id = u.id
            GROUP BY u.id
            ORDER BY zones_owned DESC
            LIMIT 10
        """)

        return {
            "status": "ok",
            "leaderboard": [dict(r) for r in rows]
        }