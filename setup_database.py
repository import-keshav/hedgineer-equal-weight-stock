import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "migrations"))
from migrations.migration_runner import run_migrations

async def main():
    try:
        await run_migrations()
        print("Database setup completed successfully!")
    except Exception as e:
        print(f"Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
