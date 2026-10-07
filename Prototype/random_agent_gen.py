import sql_functions
import psycopg
from random import randint


def connect_db():
    return psycopg.connect(
        host='localhost',
        dbname='zombie_game',
        user='postgres',
        password='0731',  # Put your postgreSQL password here
        port=5432
    )


def main():
    conn = connect_db()

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
        conn.commit()

        sql_functions.count_humans(conn=conn)
    conn.close()


if __name__ == "__main__":
    main()
