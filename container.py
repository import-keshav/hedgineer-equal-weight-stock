
import os
from src.services.stock_history_service import StockHistoryService
from src.services.index_service import IndexService
from src.services.redis_service import RedisService
from src.managers.index_data_dump_manager import IndexDataDumpManager
from src.managers.index_manager import IndexManager
from src.managers.build_index_manager import BuildIndexManager
from src.controllers.index_controller import IndexController
from src.scheduler.cron_scheduler import CronScheduler
from src.services.data_source_service import DataSourceService
from src.repositories.base_repository import BaseRepository
from src.repositories.stock_price_history_repository import StockPriceHistoryRepository

# Get database path - use test database if in test environment
db_path = os.getenv("DUCKDB_PATH", "data/hedgineer.db")
if "pytest" in os.getenv("_", "") or os.getenv("TESTING"):
    db_path = "data/test_hedgineer.db"

# Initialize base repository with connection
base_repository = BaseRepository(db_path=db_path)

# Initialize services and repositories
data_source_service = DataSourceService()
redis_service = RedisService()
stock_price_history_repository = StockPriceHistoryRepository(base_repository)
stock_history_service = StockHistoryService(
    data_source_service=data_source_service,
    repository=stock_price_history_repository
)
index_service = IndexService(repository=stock_price_history_repository)
build_index_manager = BuildIndexManager(index_service, stock_history_service)
index_manager = IndexManager(index_service, redis_service)
index_data_dump_manager = IndexDataDumpManager(stock_history_service)
index_controller = IndexController(index_manager, build_index_manager)
cron_scheduler = CronScheduler(index_data_dump_manager, build_index_manager)
