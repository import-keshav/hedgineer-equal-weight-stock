import os
import asyncio
from pathlib import Path
from typing import List
import duckdb

class MigrationRunner:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "data/hedgineer.db")
        self.migrations_dir = Path(__file__).parent
        self.connection = None
        
    def _setup_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.connection = duckdb.connect(self.db_path)
        
        self.connection.execute("DROP TABLE IF EXISTS migrations")
        self.connection.execute("""
            CREATE TABLE migrations (
                filename VARCHAR(255) NOT NULL UNIQUE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
    def _get_pending_migrations(self) -> List[Path]:
        try:
            executed = self.connection.execute("SELECT filename FROM migrations").fetchall()
            executed_files = [row[0] for row in executed]
        except Exception:
            executed_files = []
            
        return sorted([
            f for f in self.migrations_dir.glob("*.sql") 
            if f.name not in executed_files
        ])
    
    def _execute_migration(self, migration_file: Path):
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        self.connection.execute(sql_content)
        self.connection.execute(
            "INSERT INTO migrations (filename) VALUES (?)",
            [migration_file.name]
        )
    
    async def run_migrations(self):
        try:
            self._setup_database()
            pending_migrations = self._get_pending_migrations()
            
            for migration_file in pending_migrations:
                await asyncio.to_thread(self._execute_migration, migration_file)
                
        finally:
            if self.connection:
                self.connection.close()

async def run_migrations():
    runner = MigrationRunner()
    await runner.run_migrations()

if __name__ == "__main__":
    asyncio.run(run_migrations())
