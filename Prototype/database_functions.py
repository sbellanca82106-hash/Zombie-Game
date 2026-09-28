import psycopg  # Implements postgreSQL tools into Python

# Setup for Mike J's local database; Configure to your own needs
with psycopg.connect(
    host='localhost',
    dbname='zombie_game',
    user='postgres',
    password='',  # Put your postgreSQL password here
    port=5432
) as conn:

    # Creates a human with generic stats and adds it to the database
    # The first set of variables that can be edited are within the VALUES parentheses (Not 'human').
    # ^ These variables will go to the agents supertable.
    # The second set of variables that can be edited are within the SELECT parentheses (Not 'agent_id').
    # ^ These variables will go to the humans subtable.
    def create_human(conn):
        with conn.cursor() as cur:
            cur.execute("""
                        BEGIN;

                        WITH new_agent AS (
                                INSERT INTO agents(
                                        agent_type,
                                        health,
                                        speed
                                )
                                VALUES (
                                        'human',
                                        100,
                                        3
                                )
                                RETURNING agent_id
                        )

                                INSERT INTO humans (
                                        agent_id,
                                        weapon_tier,
                                        x_pos,
                                        y_pos
                                )
                                SELECT
                                        agent_id,
                                        1,
                                        0,
                                        0
                                FROM new_agent;

                                COMMIT;
                                        """)

# Creates a zombie with generic stats and adds it to the database
# The first set of variables that can be edited are within the VALUES parentheses (Not 'zombie').
# ^ These variables will go to the agents supertable.
# The second set of variables that can be edited are within the SELECT parentheses (Not 'agent_id').
# ^ These variables will go to the zombies subtable.
    def create_zombie(conn):
        with conn.cursor() as cur:
            cur.execute("""
                        BEGIN;

                        WITH new_agent AS (
                                INSERT INTO agents(
                                        agent_type,
                                        health,
                                        speed
                                )
                                VALUES (
                                        'zombie',
                                        100,
                                        3
                                )
                                RETURNING agent_id
                        		)

                                INSERT INTO zombies (
                                        agent_id,
                                        strength,
                                        x_pos,
                                        y_pos
                                )
                                SELECT
                                        agent_id,
                                        3,
                                        0,
                                        0
                                FROM new_agent;

                                COMMIT;
                                        """)

# Counts the number of humans in the database and prints the results
    def count_humans(conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM humans;")

            agent_count = cur.fetchone()[0]
        print(f"There are {agent_count} humans in the database.")

# Counts the number of zombies in the database and prints the results
    def count_zombies(conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM zombies;")

            agent_count = cur.fetchone()[0]
        print(f"There are {agent_count} zombies in the database.")

# This creates the agents supertable, as well as the humans and zombies subtables.
# I have not tested if this will cause issues if the tables already exist, but it should just throw an error.
# It also makes a type called "agent_type"
    def create_tables(conn):
        with conn.cursor() as cur:
            cur.execute("""
						BEGIN;
                        
						CREATE TYPE agent_type as ENUM ('human', 'zombie');

						CREATE TABLE agents (
								agent_id serial PRIMARY KEY,
								agent_type agent_type NOT NULL,

								is_alive boolean NOT NULL DEFAULT true,
								health integer NOT NULL DEFAULT 100,
								speed integer NOT NULL DEFAULT 1,

								UNIQUE (agent_id, agent_type),

								CONSTRAINT health_check
										CHECK (health >= 0),

								CONSTRAINT speed_check
										CHECK (speed >= 0)
						);

						CREATE TABLE humans (
								agent_id integer PRIMARY KEY,
								agent_type agent_type NOT NULL DEFAULT 'human',

								weapon_tier boolean NOT NULL DEFAULT 1,

								x_pos integer NOT NULL DEFAULT 0,
								y_pos integer NOT NULL DEFAULT 0,

								CONSTRAINT agent_type_check
										CHECK (agent_type = 'human'),

						CONSTRAINT human_agent_fk
								FOREIGN KEY (agent_id, agent_type)
								REFERENCES agents (agent_id, agent_type)
								ON DELETE CASCADE
						);

						CREATE TABLE zombies (
								agent_id integer PRIMARY KEY,
								agent_type agent_type NOT NULL DEFAULT 'zombie',

								strength integer NOT NULL DEFAULT 1,

								x_pos integer NOT NULL DEFAULT 0,
								y_pos integer NOT NULL DEFAULT 0,

								CONSTRAINT agent_type_check
										CHECK (agent_type = 'zombie'),

								CONSTRAINT zombie_agent_fk
										FOREIGN KEY (agent_id, agent_type)
										REFERENCES agents (agent_id, agent_type)
										ON DELETE CASCADE,

								CONSTRAINT strength_check
										CHECK (strength >= 0)
						);
""")

# MUST indent when putting functions
# Run functions at will here
# Must have conn as an argument in order to run the functions
    create_zombie(conn)
    count_zombies(conn)
