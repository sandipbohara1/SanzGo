# db.py
# Manages the database connection pool for the entire app.
# The pool is created once when the app starts and closed when the app stops.
# Every endpoint borrows a connection from the pool, uses it, then returns it.
# If the database is unreachable at startup, the app will not start.
import asyncio
import asyncpg                  # the PostgreSQL driver we are using

from app.config import (        # import all database connection settings
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)

# This variable holds the connection pool once it is created
# It starts as None and gets set when the app starts up
pool = None

async def connect():
    # Called once when FastAPI starts
    # Creates the connection pool and verifies the database is reachable
    # If anything fails here the app will not start — better to fail early
    global pool

    print(f"Connecting to database at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    
    try:
        # Create the connection pool
        pool = await asyncpg.create_pool(
            host = DB_HOST,
            port = DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=2,     # always keep at least 2 connections open and ready
            max_size=10     # never open more than 10 connections at once 
        )
        print("Connection pool created successfully")

    except asyncpg.InvalidPasswordError:
         # Wrong username or password in .env
        print("Database error: invalid username or password")
        print(f"   Check DB_USER and DB_PASSWORD in your .env file")
        raise
    
    except asyncpg.InvalidCatalogNameError:
        # Database name does not exist
        print(f"Database error: database '{DB_NAME}' does not exist")
        print(f"   Check DB_NAME in your .env file")
        raise

    except OSError:
        # Cannot reach the host — Docker might not be running
        print(f"Database error: cannot reach {DB_HOST}:{DB_PORT}")
        print(f"   Is Docker running? Try: docker compose up -d")
        raise

    except Exception as e:
        # Catch anything else unexpected
        print(f"Database error: {e}")
        raise

    # Verify the connection works by running a simple query (Doesn't affet the functionality)
    try:
        async with pool.acquire() as conn:
            # Check PostgreSQL version
            version = await conn.fetchval("SELECT version()")
            print(f"Connected to: {version}")

            # Check PostGIS is enabled — required for territory features
            postgis = await conn.fetchval("SELECT PostGIS_Version()")
            print(f"PostGIS version: {postgis}")

            # Check all required tables exist
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            print([row["table_name"] for row in tables])

    except Exception as e:
        print(f"Database validation failed: {e}")
        raise

async def disconnect():
    # Called once when FastAPI shuts down
    # Cleanly closes all connections in the pool
    global pool
    if pool:
        await pool.close()
        print("Database connection pool closed cleanly")


async def get_connection():
    # Used by every endpoint that needs to talk to the database
    # Borrows a connection from the pool and returns it when the request is done
    # Always use this inside an async with block:
    #   async with await get_connection() as conn:
    #       result = await conn.fetch("SELECT ...")
    if not pool:
        raise RuntimeError("Database pool is not initialised — did the app start correctly?")
    return pool.acquire()





