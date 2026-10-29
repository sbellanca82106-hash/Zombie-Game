# Test room for generating mass amounts of agents with varying stats

from random import randint

from database import database_connect
import database_functions as sql_functions


def main():
    with database_connect() as conn:
        simulation_id = sql_functions.create_simulation(
            conn,
            starting_humans=10,
            starting_zombies=0,
        )

        for _ in range(10):
            # Create a human with random stats and add it to the database.
            sql_functions.create_human(
                health=randint(80, 120),
                speed=randint(1, 5),
                weapon_tier=randint(1, 5),
                x_pos=randint(0, 100),
                y_pos=randint(0, 100),
                conn=conn,
                simulation_id=simulation_id,
                power=randint(1, 5),
            )

        sql_functions.count_humans(conn)


if __name__ == "__main__":
    main()
