# Needed to run any database related function

import psycopg


def database_connect():
    return psycopg.connect(
        host='localhost',
        dbname='zombie_game',
        user='postgres',
        password='',  # Put your postgreSQL password here
        port=5432
    )
