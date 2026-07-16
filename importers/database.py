import sqlite3
from config import DATABASE

def connect():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def cursor():
    conn = connect()
    return conn, conn.cursor()