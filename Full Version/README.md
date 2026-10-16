# Zombie Game Simulation — database agent creation update

These files preserve the existing game prompts and battle messages while saving each run's newly created agents to PostgreSQL.

## Files

- `main.py` — creates agents with the existing thread pool, then writes their initial states to the database before the first battle. Battle messages and final forces appear before the replay prompt. If database saving fails, the game continues and reports a warning to stderr.
- `database_functions.py` — adds `create_simulation`, updates `create_human` and `create_zombie` to store `simulation_id` and `power`, and returns each generated `agent_id`. Existing positional function calls still work.
- `connection.py` — the single shared database connection configuration. `database.py` remains as a compatibility wrapper for older imports.
- `data_pull.py` — reads the new simulation and power fields and uses the shared connection configuration.
- `random_agent_gen.py` — fixed import name and uses the simulation-aware creation functions.
- `migrate_agent_simulations.sql` — safe migration for an existing database.
- `requirements.txt` — Psycopg with its binary implementation, addressing the missing `pq` implementation error.

## Setup on Windows / VS Code

1. Put the `.py` files in the same project folder. Keep `connection.py` alongside the other files. The older `database.py` wrapper is included for compatibility.
2. In the VS Code terminal, install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Run `migrate_agent_simulations.sql` once against the existing `zombie_game` database using pgAdmin's Query Tool or `psql`. It adds two columns and a table without dropping existing records.
4. Configure PostgreSQL connection settings in environment variables if the defaults do not match your setup: `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, and `PGPORT`. Defaults are localhost, `zombie_game`, `postgres`, password `admin` (matching your uploaded `connection.py`), and port 5432. Set `PGPASSWORD` if your actual PostgreSQL password is different. The connection timeout defaults to 3 seconds and can be changed with `PGCONNECT_TIMEOUT`.
5. Run `main.py` as before. Console prompts and battle output remain unchanged. Each run gets a simulation ID and each created agent gets its own agent ID in PostgreSQL.

## Important scope note

This change stores the initial state of each agent for each simulation. It does not yet update records when an agent dies during battles; that is the follow-up change. Earlier simulation rows are retained rather than deleted, so each run remains identifiable.

If you want to create the schema from scratch rather than migrate an existing database, run `create_tables(conn)` from `database_functions.py` once instead of running the migration. Do not run `reset_tables()` unless you intend to drop the existing agent and simulation data.
