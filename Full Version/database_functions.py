# SQL operations used by the simulation and the interactive database helper.
from connection import database_connect


def create_simulation(conn, starting_humans, starting_zombies):
    """Create one simulation row and return its generated ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO simulations (starting_humans, starting_zombies)
            VALUES (%s, %s)
            RETURNING simulation_id;
            """,
            (starting_humans, starting_zombies),
        )
        return cur.fetchone()[0]


def create_human(
    health,
    speed,
    weapon_tier,
    x_pos,
    y_pos,
    conn,
    *,
    simulation_id=None,
    power=1,
):
    """Create a human in the shared agents table and humans subtype table.

    The original positional arguments remain supported. Simulation-created
    agents may also pass simulation_id and power as keyword-only arguments.
    Returns the generated agent_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH new_agent AS (
                INSERT INTO agents (
                    simulation_id, agent_type, health, speed, power
                )
                VALUES (%s, 'human', %s, %s, %s)
                RETURNING agent_id
            )
            INSERT INTO humans (agent_id, weapon_tier, x_pos, y_pos)
            SELECT agent_id, %s, %s, %s
            FROM new_agent
            RETURNING agent_id;
            """,
            (
                simulation_id,
                health,
                speed,
                power,
                weapon_tier,
                x_pos,
                y_pos,
            ),
        )
        return cur.fetchone()[0]


def create_zombie(
    health,
    speed,
    strength,
    x_pos,
    y_pos,
    conn,
    *,
    simulation_id=None,
    power=1,
):
    """Create a zombie in the shared agents table and zombies subtype table.

    The original positional arguments remain supported. Simulation-created
    agents may also pass simulation_id and power as keyword-only arguments.
    Returns the generated agent_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH new_agent AS (
                INSERT INTO agents (
                    simulation_id, agent_type, health, speed, power
                )
                VALUES (%s, 'zombie', %s, %s, %s)
                RETURNING agent_id
            )
            INSERT INTO zombies (agent_id, strength, x_pos, y_pos)
            SELECT agent_id, %s, %s, %s
            FROM new_agent
            RETURNING agent_id;
            """,
            (
                simulation_id,
                health,
                speed,
                power,
                strength,
                x_pos,
                y_pos,
            ),
        )
        return cur.fetchone()[0]



def update_agent_positions(conn, humans, zombies):
    """Persist the latest grid coordinates for all agents in this run."""
    human_rows = [
        (human.x_pos, human.y_pos, human.agent_id)
        for human in humans
        if human.agent_id is not None
    ]
    zombie_rows = [
        (zombie.x_pos, zombie.y_pos, zombie.agent_id)
        for zombie in zombies
        if zombie.agent_id is not None
    ]

    with conn.cursor() as cur:
        if human_rows:
            cur.executemany(
                "UPDATE humans SET x_pos = %s, y_pos = %s WHERE agent_id = %s;",
                human_rows,
            )
        if zombie_rows:
            cur.executemany(
                "UPDATE zombies SET x_pos = %s, y_pos = %s WHERE agent_id = %s;",
                zombie_rows,
            )


def mark_agents_dead(conn, agents):
    """Persist defeated agents as dead while retaining their last coordinates."""
    rows = [
        (agent.agent_id,)
        for agent in agents
        if agent.agent_id is not None
    ]
    if not rows:
        return

    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE agents SET is_alive = FALSE, health = 0 WHERE agent_id = %s;",
            rows,
        )


def delete_simulation(conn, simulation_id):
    """Delete one failed/incomplete run; agent subtype rows cascade with agents."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM simulations WHERE simulation_id = %s;",
            (simulation_id,),
        )


def finish_simulation(conn, simulation_id):
    """Record that the simulation run has ended."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE simulations SET finished_at = NOW() WHERE simulation_id = %s;",
            (simulation_id,),
        )


def count_humans(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM humans;")
        agent_count = cur.fetchone()[0]
    print(f"There are {agent_count} humans in the database.")


def count_zombies(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM zombies;")
        agent_count = cur.fetchone()[0]
    print(f"There are {agent_count} zombies in the database.")


def create_tables(conn):
    """Create the current schema in a fresh database."""
    with conn.cursor() as cur:
        cur.execute("CREATE TYPE agent_type AS ENUM ('human', 'zombie');")
        cur.execute(
            """
            CREATE TABLE simulations (
                simulation_id BIGSERIAL PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMPTZ,
                starting_humans INTEGER NOT NULL CHECK (starting_humans >= 0),
                starting_zombies INTEGER NOT NULL CHECK (starting_zombies >= 0)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE agents (
                agent_id SERIAL PRIMARY KEY,
                simulation_id BIGINT REFERENCES simulations(simulation_id)
                    ON DELETE CASCADE,
                agent_type agent_type NOT NULL,
                is_alive BOOLEAN NOT NULL DEFAULT TRUE,
                health INTEGER NOT NULL DEFAULT 100,
                speed INTEGER NOT NULL DEFAULT 1,
                power INTEGER NOT NULL DEFAULT 1,
                UNIQUE (agent_id, agent_type),
                CONSTRAINT health_check CHECK (health >= 0),
                CONSTRAINT speed_check CHECK (speed >= 0),
                CONSTRAINT power_check CHECK (power >= 0)
            );
            """
        )
        cur.execute("CREATE INDEX idx_agents_simulation_id ON agents(simulation_id);")
        cur.execute(
            """
            CREATE TABLE humans (
                agent_id INTEGER PRIMARY KEY,
                agent_type agent_type NOT NULL DEFAULT 'human',
                weapon_tier INTEGER NOT NULL DEFAULT 1,
                x_pos INTEGER NOT NULL DEFAULT 0,
                y_pos INTEGER NOT NULL DEFAULT 0,
                CONSTRAINT human_agent_type_check CHECK (agent_type = 'human'),
                CONSTRAINT human_agent_fk
                    FOREIGN KEY (agent_id, agent_type)
                    REFERENCES agents (agent_id, agent_type)
                    ON DELETE CASCADE
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE zombies (
                agent_id INTEGER PRIMARY KEY,
                agent_type agent_type NOT NULL DEFAULT 'zombie',
                strength INTEGER NOT NULL DEFAULT 1,
                x_pos INTEGER NOT NULL DEFAULT 0,
                y_pos INTEGER NOT NULL DEFAULT 0,
                CONSTRAINT zombie_agent_type_check CHECK (agent_type = 'zombie'),
                CONSTRAINT zombie_agent_fk
                    FOREIGN KEY (agent_id, agent_type)
                    REFERENCES agents (agent_id, agent_type)
                    ON DELETE CASCADE,
                CONSTRAINT strength_check CHECK (strength >= 0)
            );
            """
        )


def delete_tables(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS zombies CASCADE;")
        cur.execute("DROP TABLE IF EXISTS humans CASCADE;")
        cur.execute("DROP TABLE IF EXISTS agents CASCADE;")
        cur.execute("DROP TABLE IF EXISTS simulations CASCADE;")
        cur.execute("DROP TYPE IF EXISTS agent_type CASCADE;")


def reset_tables(conn):
    delete_tables(conn)
    create_tables(conn)


def prompt(conn):
    print('Running this file directly will show you this prompt. Below are functions that you can run directly.')
    print(
        'Functions:\n'
        '1. Create tables: create_tables(conn)\n'
        '2. Delete tables: delete_tables(conn)\n'
        '3. Reset tables: reset_tables(conn)\n'
        '4. Create human: create_human(health, speed, weapon_tier, x_pos, y_pos, conn)\n'
        '5. Create zombie: create_zombie(health, speed, strength, x_pos, y_pos, conn)\n'
        '6. Count humans: count_humans(conn)\n'
        '7. Count zombies: count_zombies(conn)\n'
    )
    try:
        choice = int(input('Enter the number of the function you want to run: '))
        if choice == 1:
            with database_connect() as conn:
                create_tables(conn)
        elif choice == 2:
            with database_connect() as conn:
                delete_tables(conn)
        elif choice == 3:
            with database_connect() as conn:
                reset_tables(conn)
        elif choice == 4:
            health = int(input('Enter health: '))
            speed = int(input('Enter speed: '))
            weapon_tier = int(input('Enter weapon tier: '))
            x_pos = int(input('Enter x position: '))
            y_pos = int(input('Enter y position: '))
            with database_connect() as conn:
                create_human(health, speed, weapon_tier, x_pos, y_pos, conn)
        elif choice == 5:
            health = int(input('Enter health: '))
            speed = int(input('Enter speed: '))
            strength = int(input('Enter strength: '))
            x_pos = int(input('Enter x position: '))
            y_pos = int(input('Enter y position: '))
            with database_connect() as conn:
                create_zombie(health, speed, strength, x_pos, y_pos, conn)
        elif choice == 6:
            with database_connect() as conn:
                count_humans(conn)
        elif choice == 7:
            with database_connect() as conn:
                count_zombies(conn)
    except ValueError:
        print('Invalid input. Please enter a number corresponding to a function in the list.')


if __name__ == "__main__":
    with database_connect() as conn:
        prompt(conn)
