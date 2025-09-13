from datetime import date, timedelta
from typing import List, Optional
from src.services.index_service import IndexService
from src.services.stock_history_service import StockHistoryService
from src.dtos.index_result import IndexComposition, IndexPerformance, IndexBuildResult
from src.constants import INDEX_BASE_VALUE, WEEKDAY_TRADING_LIMIT

class BuildIndexManager:
    def __init__(self, index_service: IndexService, stock_history_service: StockHistoryService):
        self.index_service = index_service
        self.stock_history_service = stock_history_service

    async def build_index(self, start_date: date, end_date: Optional[date] = None) -> IndexBuildResult:
        if end_date is None:
            end_date = start_date
        
        try:
            await self._ensure_stock_data_exists(start_date, end_date)
            compositions = await self._build_compositions(start_date, end_date)
            performance = await self._build_performance(start_date, end_date)
            
            await self._persist_compositions(compositions)
            await self._persist_performance(performance)
            
            trading_days = self._calculate_trading_days(start_date, end_date)
            return self._create_success_result(start_date, end_date, trading_days, len(performance))
            
        except Exception as e:
            return self._create_error_result(start_date, end_date, str(e))

    async def _ensure_stock_data_exists(self, start_date: date, end_date: date) -> None:
        current_date = start_date
        while current_date <= end_date:
            if not self._is_trading_day(current_date):
                current_date += timedelta(days=1)
                continue
            
            existing_stocks = await self.stock_history_service.get_stocks_for_date(current_date)
            if not existing_stocks:
                await self.stock_history_service.fetch_and_store_top_stocks(current_date)
            current_date += timedelta(days=1)

    async def _build_compositions(self, start_date: date, end_date: date) -> List[IndexComposition]:
        compositions = []
        current_date = start_date

        while current_date <= end_date:
            if not self._is_trading_day(current_date):
                current_date += timedelta(days=1)
                continue
            
            existing_composition = await self.index_service.get_persisted_index_composition(current_date)
            if existing_composition:
                compositions.extend(existing_composition)
            else:
                composition = await self.index_service.get_index_composition(current_date)
                if composition:
                    compositions.extend(composition)
            current_date += timedelta(days=1)

        return compositions

    async def _build_performance(self, start_date: date, end_date: date) -> List[IndexPerformance]:
        performance_list = []
        index_value = INDEX_BASE_VALUE
        current_date = start_date

        while current_date <= end_date:
            if not self._is_trading_day(current_date):
                current_date += timedelta(days=1)
                continue
            
            composition = await self.index_service.get_index_composition(current_date)
            if composition:
                performance = self._calculate_performance(composition, current_date, index_value)
                performance_list.append(performance)
                index_value = performance.index_value
            current_date += timedelta(days=1)

        return performance_list

    def _is_trading_day(self, date: date) -> bool:
        return date.weekday() < WEEKDAY_TRADING_LIMIT

    def _calculate_performance(
        self, composition: List[IndexComposition], date: date, current_index_value: float
    ) -> IndexPerformance:
        daily_return = sum(stock.return_percent for stock in composition) / len(composition)
        new_index_value = current_index_value * (1 + daily_return / 100)
        cumulative_return = ((new_index_value - INDEX_BASE_VALUE) / INDEX_BASE_VALUE) * 100
        
        return IndexPerformance(
            date=date,
            daily_return_percent=daily_return,
            cumulative_return_percent=cumulative_return,
            index_value=new_index_value,
            companies_count=len(composition)
        )

    async def _persist_compositions(self, compositions: List[IndexComposition]) -> None:
        if compositions:
            await self.index_service.persist_index_composition(compositions)

    async def _persist_performance(self, performance: List[IndexPerformance]) -> None:
        if performance:
            await self.index_service.persist_index_performance(performance)

    def _calculate_trading_days(self, start_date: date, end_date: date) -> int:
        return sum(
            1 for d in range((end_date - start_date).days + 1)
            if (start_date + timedelta(days=d)).weekday() < WEEKDAY_TRADING_LIMIT
        )

    def _create_success_result(
        self, start_date: date, end_date: date, trading_days: int, compositions_built: int
    ) -> IndexBuildResult:
        return IndexBuildResult(
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
            total_compositions_built=compositions_built,
            success=True
        )

    def _create_error_result(self, start_date: date, end_date: date, error: str) -> IndexBuildResult:
        return IndexBuildResult(
            start_date=start_date,
            end_date=end_date,
            trading_days=0,
            total_compositions_built=0,
            success=False,
            error_message=error
        )
