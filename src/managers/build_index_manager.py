from datetime import date, timedelta
from typing import List, Optional
from src.services.index_service import IndexService
from src.services.stock_history_service import StockHistoryService
from src.dtos.index_result import IndexComposition, IndexPerformance, IndexBuildResult
from src.constants import INDEX_BASE_VALUE, WEEKDAY_TRADING_LIMIT, TOP_COMPANIES_COUNT

class BuildIndexManager:
    def __init__(self, index_service: IndexService, stock_history_service: StockHistoryService):
        self.index_service = index_service
        self.stock_history_service = stock_history_service

    async def build_index(self, start_date: date, end_date: Optional[date] = None) -> IndexBuildResult:
        if end_date is None:
            end_date = start_date
        
        try:
            trading_days = self._get_trading_days(start_date, end_date)
            
            if not trading_days:
                return self._create_success_result(start_date, end_date, 0, 0, "No trading days in date range")
            
            missing_stock_dates = await self._get_missing_stock_dates(trading_days)
            if missing_stock_dates:
                await self._fetch_missing_stock_data(missing_stock_dates)
            
            missing_composition_dates = await self._get_missing_composition_dates(trading_days)
            compositions_built = 0
            if missing_composition_dates:
                await self._build_missing_compositions(missing_composition_dates)
                compositions_built = len(missing_composition_dates)
            
            missing_performance_dates = await self._get_missing_performance_dates(trading_days)
            if missing_performance_dates:
                await self._build_missing_performance(missing_performance_dates)
            
            total_processed = max(compositions_built, len(missing_performance_dates) if missing_performance_dates else 0)
            
            if not missing_stock_dates and not missing_composition_dates and not missing_performance_dates:
                return self._create_success_result(start_date, end_date, len(trading_days), 0, "Index already complete for this date range")
            
            return self._create_success_result(start_date, end_date, len(trading_days), total_processed)
            
        except Exception as e:
            return self._create_error_result(start_date, end_date, str(e))

    def _get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        trading_days = []
        current_date = start_date
        while current_date <= end_date:
            if self._is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        return trading_days

    async def _get_missing_stock_dates(self, trading_days: List[date]) -> List[date]:
        missing_dates = []
        for trading_date in trading_days:
            existing_stocks = await self.stock_history_service.get_stocks_for_date(trading_date)
            if not existing_stocks:
                missing_dates.append(trading_date)
        return missing_dates

    async def _get_missing_composition_dates(self, trading_days: List[date]) -> List[date]:
        missing_dates = []
        for trading_date in trading_days:
            existing_composition = await self.index_service.get_persisted_index_composition(trading_date)
            if not existing_composition:
                missing_dates.append(trading_date)
        return missing_dates

    async def _get_missing_performance_dates(self, trading_days: List[date]) -> List[date]:
        missing_dates = []
        for trading_date in trading_days:
            existing_performance = await self.index_service.get_persisted_index_performance(trading_date, trading_date)
            if not existing_performance:
                missing_dates.append(trading_date)
        return missing_dates

    async def _fetch_missing_stock_data(self, missing_dates: List[date]) -> None:
        for missing_date in missing_dates:
            await self.stock_history_service.fetch_and_store_top_stocks(missing_date)

    async def _build_missing_compositions(self, missing_dates: List[date]) -> None:
        all_compositions = []
        
        for missing_date in missing_dates:
            stocks = await self.stock_history_service.get_stocks_for_date(missing_date, TOP_COMPANIES_COUNT)
            if not stocks:
                continue
            
            weight_per_stock = 100.0 / len(stocks)
            compositions_for_date = []
            
            for stock in stocks:
                composition = IndexComposition(
                    date=missing_date,
                    symbol=stock.company_symbol,
                    company_name=stock.company_name,
                    weight_percent=weight_per_stock,
                    price=stock.last_traded_price,
                    return_percent=stock.one_day_return,
                    market_cap=stock.market_cap
                )
                compositions_for_date.append(composition)
            
            all_compositions.extend(compositions_for_date)
        
        if all_compositions:
            await self.index_service.persist_index_composition(all_compositions)

    async def _build_missing_performance(self, missing_dates: List[date]) -> None:
        if not missing_dates:
            return
        
        missing_dates.sort()
        performance_list = []
        
        for missing_date in missing_dates:
            previous_index_value = await self._get_previous_index_value(missing_date)
            composition = await self.index_service.get_index_composition(missing_date)
            if not composition:
                continue
            
            performance = self._calculate_performance(composition, missing_date, previous_index_value)
            performance_list.append(performance)
        
        if performance_list:
            await self.index_service.persist_index_performance(performance_list)

    async def _get_previous_index_value(self, current_date: date) -> float:
        for days_back in range(1, 11):
            previous_date = current_date - timedelta(days=days_back)
            if not self._is_trading_day(previous_date):
                continue
            
            previous_performance = await self.index_service.get_persisted_index_performance(previous_date, previous_date)
            if previous_performance:
                return previous_performance[0].index_value
        
        return INDEX_BASE_VALUE

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

    def _create_success_result(
        self, start_date: date, end_date: date, trading_days: int, compositions_built: int, skip_reason: str = None
    ) -> IndexBuildResult:
        result = IndexBuildResult(
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
            total_compositions_built=compositions_built,
            success=True
        )
        if skip_reason:
            result.error_message = skip_reason
        return result

    def _create_error_result(self, start_date: date, end_date: date, error: str) -> IndexBuildResult:
        return IndexBuildResult(
            start_date=start_date,
            end_date=end_date,
            trading_days=0,
            total_compositions_built=0,
            success=False,
            error_message=error
        )