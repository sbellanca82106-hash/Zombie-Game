# Zombie Game Simulation — grid movement and PostgreSQL persistence

## What was added

- Each human and zombie receives an integer `(x_pos, y_pos)` cell on a 100 x 100 grid at creation. Starting cells are unique when the total population fits on the grid.
- Before every battle, every surviving agent moves one cell. If an opposing agent is within a Euclidean detection radius of 10 grid cells, the agent moves one step toward the closest opponent; otherwise, it roams to a random neighboring cell. Humans target zombies only, and zombies target humans only. Diagonal movement is allowed; grid boundaries are enforced. Movement uses its own random generator so wandering does not consume the battle-result random stream.
- The initial position is written with the agent when the agent is inserted in PostgreSQL. After every battle's movement phase, current positions are written to the subtype tables (`humans` and `zombies`). Defeated agents are marked `is_alive = FALSE` and `health = 0`, and each simulation is marked finished at the end.
- Database failures are sent to stderr and do not stop the original simulation loop or change the normal battle-message format.
- `connection.py` is the single source of connection settings. It defaults to the supplied settings (`localhost`, database `zombie_game`, user `postgres`, password `admin`, port `5432`); environment variables can override them.

## Files

- `main.py` — original battle simulation plus grid movement, chasing, and per-battle position persistence.
- `database_functions.py` — create simulation/agent records, persist positions, mark casualties, and finish a simulation.
- `connection.py` — shared PostgreSQL connection function.
- `database.py` — compatibility wrapper for older imports.
- `data_pull.py` — read and update saved agents.
- `random_agent_gen.py` — helper script for test records.
- `migrate_agent_simulations.sql` — adds simulation tracking, power, and coordinate columns without dropping existing data.

## Setup

1. Keep the Python files together in your project directory.
2. Install Psycopg:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Run `migrate_agent_simulations.sql` once against the existing `zombie_game` database. It preserves existing rows. Do not run `reset_tables()` unless you intentionally want to drop stored data.
4. Verify the defaults in `connection.py`, or set `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, and `PGPORT` in the terminal environment.
5. Start `main.py` as usual.

## Notes

The battle outcome/casualty calculation is unchanged; spatial movement changes agents' positions and saved state but does not yet change battle strength based on proximity. Movement occurs once immediately before each battle's existing population-level calculation. The default detection radius is configured by `DETECTION_RADIUS` in `main.py`.


## Multithreading added

- Agent objects are created in the existing `ThreadPoolExecutor` worker pool.
- Initial database inserts are split into bounded chunks. Each worker uses its own PostgreSQL connection and transaction; a connection is never shared concurrently between threads. The main thread attaches generated database IDs after all chunks finish.
- Neighbor finding runs as parallel tasks for each agent using the same per-run executor. Every task reads a snapshot of all coordinates, and new positions are applied only after all movement tasks finish.
- Per-round coordinate persistence and casualty updates are chunked and processed concurrently with a separate PostgreSQL connection per worker.
- If initial agent persistence partially fails, the incomplete simulation record is deleted to cascade-clean any already-committed agent rows. If a later parallel state update fails, the simulation continues and further DB writes are disabled; a warning is written to stderr.

The SQL schema migration script (`migrate_agent_simulations.sql`) should still be run once, by one process, before starting the app. Schema DDL is intentionally not parallelized: simultaneous `ALTER TABLE`/`CREATE TABLE` operations against the same schema can race and lock each other. The data insertion and state persistence operations are what run in parallel.
