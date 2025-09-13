import pytest
import asyncio
import os
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import AsyncMock, Mock
from src.managers.index_manager import IndexManager
from src.managers.build_index_manager import BuildIndexManager
from src.services.redis_service import RedisService
from src.services.index_service import IndexService
from src.repositories.base_repository import BaseRepository
from src.repositories.stock_price_history_repository import StockPriceHistoryRepository
from src.dtos.index_result import IndexComposition, IndexPerformance, IndexBuildResult


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary database file for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_hedgineer.db")
    yield db_path
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_base_repository(test_db_path):
    """Create a BaseRepository with test database"""
    # Set environment variable for test database
    os.environ["TESTING"] = "1"
    os.environ["DUCKDB_PATH"] = test_db_path
    
    base_repo = BaseRepository(db_path=test_db_path)
    yield base_repo
    base_repo.close()
    
    # Clean up environment
    os.environ.pop("TESTING", None)
    os.environ.pop("DUCKDB_PATH", None)


@pytest.fixture
def test_stock_repository(test_base_repository):
    """Create a StockPriceHistoryRepository with test database"""
    return StockPriceHistoryRepository(test_base_repository)



@pytest.fixture
def mock_redis_service():
    return Mock(spec=RedisService)


@pytest.fixture
def mock_index_service():
    mock = Mock(spec=IndexService)
    mock.repository = Mock()
    mock.repository.persist_index_composition = AsyncMock(return_value=True)
    mock.repository.persist_index_performance = AsyncMock(return_value=True)
    mock.repository.get_persisted_index_performance = AsyncMock(return_value=[])
    mock.repository.get_persisted_index_composition = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_build_index_manager():
    return Mock(spec=BuildIndexManager)


@pytest.fixture
def mock_index_manager():
    return Mock(spec=IndexManager)


@pytest.fixture
def sample_index_composition():
    return [
        IndexComposition(
            date=date(2025, 9, 10),
            symbol="AAPL",
            company_name="Apple Inc.",
            weight_percent=1.0,
            market_cap=2580000000000.0,
            price=173.32,
            return_percent=-1.52
        ),
        IndexComposition(
            date=date(2025, 9, 10),
            symbol="MSFT",
            company_name="Microsoft Corporation",
            weight_percent=1.0,
            market_cap=2450000000000.0,
            price=329.15,
            return_percent=0.87
        )
    ]


@pytest.fixture
def sample_index_performance():
    return [
        IndexPerformance(
            date=date(2025, 9, 10),
            daily_return_percent=0.2495,
            cumulative_return_percent=0.2495,
            index_value=1002.495,
            companies_count=100
        ),
        IndexPerformance(
            date=date(2025, 9, 11),
            daily_return_percent=-0.2784,
            cumulative_return_percent=-0.0290,
            index_value=999.710,
            companies_count=100
        )
    ]


@pytest.fixture
def sample_build_result():
    return IndexBuildResult(
        start_date=date(2025, 9, 10),
        end_date=date(2025, 9, 12),
        trading_days=3,
        total_compositions_built=3,
        success=True
    )
