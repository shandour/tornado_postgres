import argparse

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

from local_settings import local_settings_dict


parser = argparse.ArgumentParser()
engine = create_engine(local_settings_dict['database'])


def create_db():
    with engine.connect() as conn:
        try:
            res = conn.execute(
                "SELECT COUNT(*) FROM bloggers LIMIT 1")
            res.fetchone()
            print('Database already exists')
        except (ProgrammingError, psycopg2.ProgrammingError):
            with open(local_settings_dict['schema_path']) as f:
                schema = f.read()
                conn.execute(schema)
                print('Created new database')


def drop_db():
    with engine.connect() as conn:
        conn.execute("DROP SCHEMA public CASCADE;"
                     "CREATE SCHEMA public;")
    print('Dropped db')


FUNCTION_MAP = {'create_db': create_db,
                'drop_db': drop_db}

parser.add_argument('command', choices=FUNCTION_MAP.keys())


if __name__ == '__main__':
    arguments = parser.parse_args()
    FUNCTION_MAP[arguments.command]()
