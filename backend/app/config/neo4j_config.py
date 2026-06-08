import os
from neo4j import GraphDatabase
from contextlib import contextmanager

NEO4J_HOST = "127.0.0.1" 
NEO4J_PORT = "7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Thuc2022005" 

NEO4J_URI = f"bolt://{NEO4J_HOST}:{NEO4J_PORT}"

class Neo4jConnection:
    def __init__(self):
        self._driver = None

    def connect(self):
        """Khởi tạo một driver kết nối duy nhất (Singleton) cho toàn ứng dụng"""
        if not self._driver:
            try:
                self._driver = GraphDatabase.driver(
                    NEO4J_URI, 
                    auth=(NEO4J_USER, NEO4J_PASSWORD),
                    max_connection_lifetime=3600, 
                    max_connection_pool_size=50  ,  
                    connection_timeout=30.0, 
                    keep_alive=True     
                )
                print("⚡ Kết nối tới Neo4j Graph Database thành công!")
            except Exception as e:
                print(f"❌ Lỗi kết nối Neo4j: {e}")
                raise e

    def get_driver(self):
        if not self._driver:
            self.connect()
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

# Khởi tạo đối tượng toàn cục để quản lý kết nối
neo4j_conn = Neo4jConnection()


def get_neo4j_session():
    driver = neo4j_conn.get_driver()
    # Mở một session mới cho mỗi request
    with driver.session(database = "castrelationships") as session:
        yield session