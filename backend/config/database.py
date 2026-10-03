"""
Database connection manager.
Uses psycopg2 to connect to PostgreSQL.
Reads credentials from .env file.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load .env from config folder
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host'    : os.getenv('DB_HOST', 'localhost'),
    'port'    : os.getenv('DB_PORT', '5432'),
    'dbname'  : os.getenv('DB_NAME', 'arthsathi'),
    'user'    : os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
}

def get_connection():
    """
    Returns a new PostgreSQL connection.
    Always use this inside a try/finally block and close after use.
    """
    return psycopg2.connect(**DB_CONFIG)

def get_cursor(conn):
    """
    Returns a cursor that gives results as dicts
    instead of tuples — much easier to work with.
    """
    return conn.cursor(cursor_factory=RealDictCursor)
