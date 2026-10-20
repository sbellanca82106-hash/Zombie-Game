"""Shared PostgreSQL connection settings for the Zombie Game project.

Configure PGHOST, PGDATABASE, PGUSER, PGPASSWORD, and PGPORT in the
process environment if your local PostgreSQL settings differ from the defaults.
"""

import os
import psycopg


def database_connect(*, host=None, dbname=None, user=None, password=None, port=None):
    """Open a PostgreSQL connection using shared defaults and optional overrides."""
    resolved_host = host if host is not None else os.getenv("PGHOST", "localhost")
    resolved_dbname = dbname if dbname is not None else os.getenv("PGDATABASE", "zombie_game")
    resolved_user = user if user is not None else os.getenv("PGUSER", "postgres")
    resolved_password = password if password is not None else os.getenv("PGPASSWORD", "")
    resolved_port = port if port is not None else os.getenv("PGPORT", "5432")

    return psycopg.connect(
        host=resolved_host,
        dbname=resolved_dbname,
        user=resolved_user,
        password=resolved_password,
        port=int(resolved_port),
        connect_timeout=int(os.getenv("PGCONNECT_TIMEOUT", "3")),
    )
