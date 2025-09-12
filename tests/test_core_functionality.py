import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock
from src.managers.build_index_manager import BuildIndexManager
from src.managers.index_manager import IndexManager
from src.services.redis_service import RedisService
from src.services.index_service import IndexService
from src.dtos.index_result import IndexComposition, IndexPerformance, IndexBuildResult, CompositionChange


class TestBuildIndexManager:
    
    @pytest.mark.asyncio
    async def test_build_index_success_single_day(self):
        mock_service = Mock()
        mock_service.get_index_composition = AsyncMock(return_value=[
            IndexComposition(
                date=date(2025, 9, 10),
                symbol="AAPL",
                company_name="Apple Inc.",
                weight_percent=1.0,
                market_cap=2580000000000.0,
                price=173.32,
                return_percent=1.5
            )
        ])
        mock_service.repository = Mock()
        mock_service.repository.persist_index_composition = AsyncMock(return_value=True)
        mock_service.repository.persist_index_performance = AsyncMock(return_value=True)
        
        manager = BuildIndexManager(mock_service)
        result = await manager.build_index(date(2025, 9, 10))
        
        assert result.success is True
        assert result.trading_days == 1
        assert result.total_compositions_built == 1

    def test_trading_day_logic(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        
        assert manager._is_trading_day(date(2025, 9, 10)) is True
        assert manager._is_trading_day(date(2025, 9, 13)) is False
        assert manager._is_trading_day(date(2025, 9, 14)) is False

    def test_calculate_trading_days_range(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        
        result = manager._calculate_trading_days(date(2025, 9, 9), date(2025, 9, 15))
        assert result == 5

    def test_performance_calculation(self):
        mock_service = Mock()
        manager = BuildIndexManager(mock_service)
        
        composition = [
            IndexComposition(
                date=date(2025, 9, 10),
                symbol="AAPL",
                company_name="Apple Inc.",
                weight_percent=1.0,
                market_cap=2580000000000.0,
                price=173.32,
                return_percent=2.0
            ),
            IndexComposition(
                date=date(2025, 9, 10),
                symbol="MSFT",
                company_name="Microsoft Corporation",
                weight_percent=1.0,
                market_cap=2450000000000.0,
                price=329.15,
                return_percent=-1.0
            )
        ]
        
        result = manager._calculate_performance(composition, date(2025, 9, 10), 1000.0)
        
        assert result.date == date(2025, 9, 10)
        assert result.daily_return_percent == 0.5
        assert result.companies_count == 2
        assert abs(result.index_value - 1005.0) < 0.001


class TestIndexManager:
    
    @pytest.mark.asyncio
    async def test_get_performance_from_cache(self):
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
        assert result[0].companies_count == 100

    @pytest.mark.asyncio
    async def test_get_composition_from_cache(self):
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
        assert result[0].weight_percent == 1.0

    @pytest.mark.asyncio
    async def test_get_composition_changes_from_cache(self):
        mock_index_service = Mock()
        mock_redis_service = Mock()
        
        mock_redis_service.get_composition_changes = AsyncMock(return_value=[{
            "date": "2025-09-10",
            "symbol": "NVDA",
            "company_name": "NVIDIA Corporation",
            "change_type": "entered",
            "previous_weight_percent": 0.0,
            "new_weight_percent": 1.0
        }])
        
        manager = IndexManager(mock_index_service, mock_redis_service)
        result = await manager.get_composition_changes(date(2025, 9, 10), date(2025, 9, 10))
        
        assert len(result) == 1
        assert result[0].symbol == "NVDA"
        assert result[0].change_type == "entered"


class TestRedisService:
    
    def test_cache_key_generation(self):
        service = RedisService()
        
        key1 = service._make_key("performance", start_date=date(2025, 9, 10), end_date=date(2025, 9, 11))
        key2 = service._make_key("composition", date=date(2025, 9, 10))
        key3 = service._make_key("simple")
        
        assert "performance" in key1
        assert "2025-09-10" in key1
        assert "2025-09-11" in key1
        assert "composition:date:2025-09-10" == key2
        assert "simple" == key3

    @pytest.mark.asyncio
    async def test_cache_operations(self):
        service = RedisService()
        mock_client = Mock()
        service._client = mock_client
        
        mock_client.get.return_value = '{"test": "data"}'
        result = await service.get("test_key")
        assert result == {"test": "data"}
        
        mock_client.setex.return_value = True
        result = await service.set("test_key", {"test": "data"})
        assert result is True
        
        mock_client.get.side_effect = Exception("Redis error")
        result = await service.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_index_specific_methods(self):
        service = RedisService()
        
        service.get = AsyncMock(return_value=[{"test": "data"}])
        service.set = AsyncMock(return_value=True)
        
        result = await service.get_index_performance(date(2025, 9, 10), date(2025, 9, 11))
        assert result == [{"test": "data"}]
        
        success = await service.set_index_performance(date(2025, 9, 10), date(2025, 9, 11), [{"test": "data"}])
        assert success is True
        
        result = await service.get_index_composition(date(2025, 9, 10))
        assert result == [{"test": "data"}]
        
        success = await service.set_index_composition(date(2025, 9, 10), [{"test": "data"}])
        assert success is True


class TestDataModels:
    
    def test_index_composition_model(self):
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
        assert comp.return_percent == -1.52
        
        data = comp.model_dump()
        assert data["symbol"] == "AAPL"
        assert data["date"] == date(2025, 9, 10)

    def test_index_performance_model(self):
        perf = IndexPerformance(
            date=date(2025, 9, 10),
            daily_return_percent=0.25,
            cumulative_return_percent=0.25,
            index_value=1002.5,
            companies_count=100
        )
        
        assert perf.index_value == 1002.5
        assert perf.companies_count == 100
        
        data = perf.model_dump()
        assert data["daily_return_percent"] == 0.25

    def test_composition_change_model(self):
        change = CompositionChange(
            date=date(2025, 9, 10),
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            change_type="entered",
            previous_weight_percent=0.0,
            new_weight_percent=1.0
        )
        
        assert change.symbol == "NVDA"
        assert change.change_type == "entered"
        assert change.new_weight_percent == 1.0

    def test_build_result_models(self):
        success_result = IndexBuildResult(
            start_date=date(2025, 9, 10),
            end_date=date(2025, 9, 12),
            trading_days=3,
            total_compositions_built=3,
            success=True
        )
        
        assert success_result.success is True
        assert success_result.trading_days == 3
        assert success_result.error_message is None
        
        error_result = IndexBuildResult(
            start_date=date(2025, 9, 10),
            end_date=date(2025, 9, 12),
            trading_days=0,
            total_compositions_built=0,
            success=False,
            error_message="Test error"
        )
        
        assert error_result.success is False
        assert error_result.error_message == "Test error"


class TestBusinessLogic:
    
    def test_equal_weight_calculation(self):
        from src.constants import TOP_COMPANIES_COUNT
        
        weight_per_company = 100.0 / TOP_COMPANIES_COUNT
        assert weight_per_company == 1.0
        
        total_weight = weight_per_company * TOP_COMPANIES_COUNT
        assert total_weight == 100.0

    def test_index_value_progression(self):
        from src.constants import INDEX_BASE_VALUE
        
        initial_value = INDEX_BASE_VALUE
        daily_return_1 = 2.0
        daily_return_2 = -1.0
        
        value_after_day_1 = initial_value * (1 + daily_return_1 / 100)
        value_after_day_2 = value_after_day_1 * (1 + daily_return_2 / 100)
        
        assert value_after_day_1 == 1020.0
        assert value_after_day_2 == 1009.8
        
        cumulative_return = ((value_after_day_2 - INDEX_BASE_VALUE) / INDEX_BASE_VALUE) * 100
        assert abs(cumulative_return - 0.98) < 0.01

    def test_constants_validity(self):
        from src.constants import (
            TOP_COMPANIES_COUNT, INDEX_BASE_VALUE, WEEKDAY_TRADING_LIMIT,
            MAX_COMPANY_SYMBOL_LENGTH, MAX_COMPANY_NAME_LENGTH
        )
        
        assert TOP_COMPANIES_COUNT == 100
        assert INDEX_BASE_VALUE == 1000.0
        assert WEEKDAY_TRADING_LIMIT == 5
        assert MAX_COMPANY_SYMBOL_LENGTH == 30
        assert MAX_COMPANY_NAME_LENGTH == 100
