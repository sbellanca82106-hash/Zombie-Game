"""Shared PostgreSQL connection settings for the Zombie Game project.

The defaults match the supplied connection.py. Set PGHOST, PGDATABASE,
PGUSER, PGPASSWORD, PGPORT, or PGCONNECT_TIMEOUT in the environment to
override them without editing source code.
"""

import os
import psycopg


def database_connect(*, host=None, dbname=None, user=None, password=None, port=None):
    """Open PostgreSQL using shared defaults and optional per-call overrides."""
    resolved_host = host if host is not None else os.getenv("PGHOST", "localhost")
    resolved_dbname = dbname if dbname is not None else os.getenv("PGDATABASE", "zombie_game")
    resolved_user = user if user is not None else os.getenv("PGUSER", "postgres")
    # The uploaded connection.py used 'admin' as its password. Keep that as
    # the local default, while allowing PGPASSWORD to override it.
    resolved_password = password if password is not None else os.getenv("PGPASSWORD", "admin")
    resolved_port = port if port is not None else os.getenv("PGPORT", "5432")

    return psycopg.connect(
        host=resolved_host,
        dbname=resolved_dbname,
        user=resolved_user,
        password=resolved_password,
        port=int(resolved_port),
        connect_timeout=int(os.getenv("PGCONNECT_TIMEOUT", "3")),
    )
