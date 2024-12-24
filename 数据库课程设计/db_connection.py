import mysql.connector
from mysql.connector import pooling


class DatabaseConnection:
    def __init__(self):
        self.dbconfig = {
            "host": "localhost",
            "user": "root",
            "password": "20050204Aa#*",
            "database": "ims"
        }

    def get_connection(self):
        return mysql.connector.connect(**self.dbconfig)

    def execute_query(self, query, params=None):
        """执行数据库查询"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"Error executing query: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def fetch_one(self, query, params=None):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def fetch_all(self, query, params=None):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            print(f"Debug - Executing query: {query}")
            print(f"Debug - Query params: {params}")
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            print(f"Debug - Query results: {results}")
            return results
        except Exception as e:
            print(f"Error in fetch_all: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def start_transaction(self):
        """开始事务"""
        self.connection = self.get_connection()
        self.connection.autocommit = False

    def commit(self):
        """提交事务"""
        if self.connection:
            self.connection.commit()

    def rollback(self):
        """回滚事务"""
        if self.connection:
            self.connection.rollback()