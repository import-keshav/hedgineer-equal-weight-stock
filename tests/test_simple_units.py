import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock
from src.managers.build_index_manager import BuildIndexManager
from src.managers.index_manager import IndexManager
from src.services.redis_service import RedisService
from src.dtos.index_result import IndexComposition, IndexPerformance, IndexBuildResult


class TestBuildIndexManagerSimple:
    
    def test_is_trading_day_weekday(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        assert manager._is_trading_day(date(2025, 9, 10)) is True

    def test_is_trading_day_weekend(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        assert manager._is_trading_day(date(2025, 9, 13)) is False

    def test_calculate_trading_days(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        result = manager._calculate_trading_days(date(2025, 9, 9), date(2025, 9, 11))
        assert result == 3

    def test_calculate_performance(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        composition = [IndexComposition(
            date=date(2025, 9, 10),
            symbol="AAPL",
            company_name="Apple Inc.",
            weight_percent=1.0,
            market_cap=2580000000000.0,
            price=173.32,
            return_percent=-1.52
        )]
        
        result = manager._calculate_performance(composition, date(2025, 9, 10), 1000.0)
        
        assert result.date == date(2025, 9, 10)
        assert result.daily_return_percent == -1.52
        assert result.companies_count == 1


class TestRedisServiceSimple:
    
    def test_make_key_with_dates(self):
        service = RedisService()
        key = service._make_key("test", start_date=date(2025, 9, 10), end_date=date(2025, 9, 11))
        expected = "test:end_date:2025-09-11:start_date:2025-09-10"
        assert key == expected

    def test_make_key_single_date(self):
        service = RedisService()
        key = service._make_key("performance", date=date(2025, 9, 10))
        expected = "performance:date:2025-09-10"
        assert key == expected

    @pytest.mark.asyncio
    async def test_get_success(self):
        service = RedisService()
        mock_client = Mock()
        mock_client.get.return_value = '{"key": "value"}'
        service._client = mock_client
        
        result = await service.get("test_key")
        
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_set_success(self):
        service = RedisService()
        mock_client = Mock()
        mock_client.setex.return_value = True
        service._client = mock_client
        
        result = await service.set("test_key", {"data": "value"})
        
        assert result is True


class TestIndexManagerSimple:
    
    @pytest.mark.asyncio
    async def test_get_index_performance_from_cache(self):
        mock_index_service = Mock()
        mock_redis_service = Mock()
        mock_redis_service.get_index_performance = AsyncMock(return_value=[{
            "date": "2025-09-10",
            "daily_return_percent": 0.25,
            "cumulative_return_percent": 0.25,
            "index_value": 1002.5,
            "companies_count": 100
        }])
        
        manager = IndexManager(mock_index_service, mock_redis_service)
        result = await manager.get_index_performance(date(2025, 9, 10), date(2025, 9, 10))
        
        assert len(result) == 1
        assert result[0].index_value == 1002.5

    @pytest.mark.asyncio
    async def test_get_index_composition_from_cache(self):
        mock_index_service = Mock()
        mock_redis_service = Mock()
        mock_redis_service.get_index_composition = AsyncMock(return_value=[{
            "date": "2025-09-10",
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "weight_percent": 1.0,
            "market_cap": 2580000000000.0,
            "price": 173.32,
            "return_percent": -1.52
        }])
        
        manager = IndexManager(mock_index_service, mock_redis_service)
        result = await manager.get_index_composition(date(2025, 9, 10))
        
        assert len(result) == 1
        assert result[0].symbol == "AAPL"


class TestModelsAndDTOs:
    
    def test_index_composition_creation(self):
        comp = IndexComposition(
            date=date(2025, 9, 10),
            symbol="AAPL",
            company_name="Apple Inc.",
            weight_percent=1.0,
            market_cap=2580000000000.0,
            price=173.32,
            return_percent=-1.52
        )
        
        assert comp.symbol == "AAPL"
        assert comp.weight_percent == 1.0

    def test_index_performance_creation(self):
        perf = IndexPerformance(
            date=date(2025, 9, 10),
            daily_return_percent=0.25,
            cumulative_return_percent=0.25,
            index_value=1002.5,
            companies_count=100
        )
        
        assert perf.index_value == 1002.5
        assert perf.companies_count == 100

    def test_index_build_result_success(self):
        result = IndexBuildResult(
            start_date=date(2025, 9, 10),
            end_date=date(2025, 9, 12),
            trading_days=3,
            total_compositions_built=3,
            success=True
        )
        
        assert result.success is True
        assert result.trading_days == 3

    def test_index_build_result_error(self):
        result = IndexBuildResult(
            start_date=date(2025, 9, 10),
            end_date=date(2025, 9, 12),
            trading_days=0,
            total_compositions_built=0,
            success=False,
            error_message="Test error"
        )
        
        assert result.success is False
        assert result.error_message == "Test error"
