# config.py
# Loads all environment variables the app needs to run.
# Every other file imports from here — nothing reads .env directly.
# If a required value is missing, the app crashes immediately with a clear message
# rather than failing silently later with a confusing error.

from dotenv import load_dotenv  # reads the .env file into the environment
import os                       # lets us read environment variables

# Read the .env file and load all values into the environment
load_dotenv()


# --- Database ---
# Connection details for the PostgreSQL database running in Docker

DB_HOST = os.getenv("DB_HOST")          # the machine the database is running on
if not DB_HOST:
    raise ValueError("DB_HOST is missing from .env")

DB_PORT = os.getenv("DB_PORT")          # the port PostgreSQL is listening on
if not DB_PORT:
    raise ValueError("DB_PORT is missing from .env")
DB_PORT = int(DB_PORT)                  # convert from string to integer

DB_NAME = os.getenv("DB_NAME")          # the name of the database inside PostgreSQL
if not DB_NAME:
    raise ValueError("DB_NAME is missing from .env")

DB_USER = os.getenv("DB_USER")          # the database login username
if not DB_USER:
    raise ValueError("DB_USER is missing from .env")

DB_PASSWORD = os.getenv("DB_PASSWORD")  # the database login password
if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD is missing from .env")


# --- JWT Authentication ---
# JSON Web Tokens are used to authenticate every API request after login

JWT_SECRET = os.getenv("JWT_SECRET")            # secret key used to sign tokens
if not JWT_SECRET:
    raise ValueError("JWT_SECRET is missing from .env")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")      # signing algorithm — we use HS256
if not JWT_ALGORITHM:
    raise ValueError("JWT_ALGORITHM is missing from .env")

JWT_EXPIRY_HOURS = os.getenv("JWT_EXPIRY_HOURS")  # how long a token stays valid
if not JWT_EXPIRY_HOURS:
    raise ValueError("JWT_EXPIRY_HOURS is missing from .env")
JWT_EXPIRY_HOURS = int(JWT_EXPIRY_HOURS)          # convert from string to integer


# --- App ---

APP_ENV = os.getenv("APP_ENV")  # current environment — 'development' or 'production'
if not APP_ENV:
    raise ValueError("APP_ENV is missing from .env")