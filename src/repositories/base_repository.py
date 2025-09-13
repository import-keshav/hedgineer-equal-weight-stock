import os
import duckdb
from typing import Optional


class BaseRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "data/hedgineer.db")
        self.connection = None
        self._ensure_db_directory()
        self._initialize_connection()
    
    def _ensure_db_directory(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _initialize_connection(self):
        try:
            self.connection = duckdb.connect(self.db_path)
        except Exception as e:
            raise Exception(f"Failed to initialize DuckDB connection: {e}")
    
    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __del__(self):
        self.close()
