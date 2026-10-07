import sql_functions
from database import database_connect
from random import randint


def main():
    with database_connect() as conn:
        for i in range(10):
            # Create a human with random stats and add it to the database
            sql_functions.create_human(
                conn=conn,
                health=randint(80, 120),
                speed=randint(1, 5),
                weapon_tier=randint(1, 5),
                x_pos=randint(0, 100),
                y_pos=randint(0, 100)
            )

        sql_functions.count_humans(conn=conn)


if __name__ == "__main__":
    main()
