import sqlite3


class Attack:

    def __init__(self, database):
        self.database = database

    async def build(self, schema):
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                cursor.executescript(schema)
                conn.commit()
        except Exception as exc:
            print('! error building db : {}'.format(exc))

    async def get(self, table, criteria=None):
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = 'SELECT * FROM %s ' % table
            if criteria:
                where = next(iter(criteria))
                value = criteria.pop(where)
                if value:
                    sql += (' WHERE %s = "%s"' % (where, value))
                    for k, v in criteria.items():
                        sql += (' AND %s = "%s"' % (k, v))
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(ix) for ix in rows]

    async def insert(self, table, data):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            columns = ', '.join(data.keys())
            temp = ['?' for i in range(len(data.values()))]
            placeholders = ', '.join(temp)
            sql = 'INSERT INTO {} ({}) VALUES ({})'.format(table, columns, placeholders)
            cursor.execute(sql, tuple(data.values()))
            id = cursor.lastrowid
            conn.commit()
            return id

    async def update(self, table, key, value, data):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            for k, v in data.items():
                sql = 'UPDATE {} SET {} = (?) WHERE {} = "{}"'.format(table, k, key, value)
                cursor.execute(sql, (v,))
            conn.commit()

    async def delete(self, table, data):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM %s ' % table
            where = next(iter(data))
            value = data.pop(where)
            sql += (' WHERE %s = "%s"' % (where, value))
            for k, v in data.items():
                sql += (' AND %s = "%s"' % (k, v))
            cursor.execute(sql)
            conn.commit()

    async def raw_query(self, query, one=False):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rv = cursor.fetchall()
            conn.commit()
            return rv[0] if rv else None if one else rv

    async def raw_select(self, sql):
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(ix) for ix in rows]

    async def raw_update(self, sql):
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()