"""
Database Connection Module

Provides database connection management using Flask's application context.
Handles connection lifecycle and database initialization.
"""

import sqlite3
from flask import current_app, g
from pathlib import Path


def get_db():
    """
    Get Database Connection (Request-scoped)
    
    Returns a SQLite database connection for the current Flask request.
    Uses Flask's 'g' object to cache the connection per request, ensuring
    one connection per request lifecycle.
    
    Returns:
        sqlite3.Connection object with row_factory set to sqlite3.Row
        (allows dictionary-like access: row['column_name'])
    """
    if "db" not in g:
        db_path = current_app.config.get("DATABASE")
        if not db_path:
            instance_path = Path(current_app.root_path).parent
            db_path = instance_path / "client_contact_manager.sqlite"
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """
    Close Database Connection
    
    Flask teardown handler that closes the database connection at the end
    of each request. Registered in app.py via app.teardown_appcontext().
    
    This ensures proper resource cleanup and prevents connection leaks.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """
    Initialize Database Schema
    
    Creates all database tables, indexes, and constraints by executing
    the SQL statements in db/schema.sql.
    
    This should be called once when setting up the application.
    Visit /init-db route to run this function.
    """
    db = get_db()
    schema_path = Path(current_app.root_path) / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()

