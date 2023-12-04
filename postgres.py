import psycopg2, psycopg2.extras

class Postgres:
    def __init__(self, host: str='localhost', user: str='postgres', password: str='postgres', database: str='comment'):
        self.conn = psycopg2.connect(database=database, user=user, password=password, host=host)
        self.conn.set_session(autocommit=True)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

if __name__ == "__main__":
    postgres = Postgres(host = "database")
    postgres.cursor.execute('select * from webpage limit 1')
    ret = postgres.cursor.fetchone()
    print([x for x in ret.keys()])
