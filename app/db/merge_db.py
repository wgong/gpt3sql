#!/usr/bin/env python
# coding: utf-8

# Merge `GPT-3 log` data between 2 sqlite databases

import sys
import sqlite3
import pandas as pd

DELIMITOR = ","

class DBConn(object):
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
    def __enter__(self):
        return self.conn
    def __exit__(self, type, value, traceback):
        self.conn.close()

def get_data(db_file, table_name):
    with DBConn(db_file) as _conn:
        sql_stmt = f'''
        SELECT uuid||'{DELIMITOR}'||ts as uuid_ts from {table_name};
        '''
        return pd.read_sql(sql_stmt, _conn)

def list2sql_str(l):
    """convert a list into SQL in string
    """
    return str(l).replace("[", "(").replace("]", ")")

def merge_logs(src_db, tgt_db="gpt3sql.sqlite", table_name="t_gpt3_log"):
    
    df_src = get_data(src_db, table_name)
    df_tgt = get_data(tgt_db, table_name)

    uuid_ts_src = df_src["uuid_ts"].to_list()
    uuid_ts_tgt = df_tgt["uuid_ts"].to_list()

    uuid_update = [i.split(DELIMITOR)[0] for i in (set(uuid_ts_src) - set(uuid_ts_tgt))]

    if uuid_update:

        # fetch new/updated row from src
        with DBConn(src_db) as _conn:
            sql_stmt = f'''
            SELECT * from {table_name} where uuid in {list2sql_str(uuid_update)} ;
            '''
            df_src = pd.read_sql(sql_stmt, _conn)

        with DBConn(tgt_db) as _conn:
            # remove old rows in tgt
            delete_sql = f"""
                delete from {table_name} where uuid in {list2sql_str(uuid_update)} ;
            """
            cur = _conn.cursor()
            cur.executescript(delete_sql)
            _conn.commit()

            # append to tgt
            df_src.to_sql(table_name, _conn, if_exists='append', index=False)
            _conn.commit()  

    return uuid_update


if __name__ == "__main__":
	if len(sys.argv) > 1:
		src_db = sys.argv[1]
		uuid_update = merge_logs(src_db)
		if uuid_update:
			print(f"Merged the following records from '{src_db}' DB:\n\t{uuid_update}")
		else:
			print("Nothing to merge")
	else:
		print("[Error] source DB file missing!")




