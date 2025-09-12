import logging
from datetime import date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.constants import DAILY_CRON_HOUR, DAILY_CRON_MINUTE, MARKET_CLOSED_WEEKENDS, DEFAULT_BACKFILL_DAYS
from src.managers.index_data_dump_manager import IndexDataDumpManager

logger = logging.getLogger(__name__)


class CronScheduler:
    def __init__(self, index_data_dump_manager: IndexDataDumpManager):
        self.manager = index_data_dump_manager
        self.scheduler = AsyncIOScheduler()
        
    async def start(self):
        logger.info("Starting cron scheduler")
        await self._run_initial_backfill()
        self._schedule_daily_job()
        self.scheduler.start()
        logger.info(f"Cron job scheduled for daily execution at {DAILY_CRON_HOUR:02d}:{DAILY_CRON_MINUTE:02d}")
        
    async def stop(self):
        logger.info("Stopping cron scheduler")
        self.scheduler.shutdown(wait=True)
        
    def _schedule_daily_job(self):
        self.scheduler.add_job(
            self._daily_data_ingestion,
            'cron',
            hour=DAILY_CRON_HOUR,
            minute=DAILY_CRON_MINUTE,
            id='daily_stock_data_ingestion'
        )
        
    async def _run_initial_backfill(self):
        try:
            available_dates = await self.manager.get_available_dates()
            
            if not available_dates:
                start_date = date.today() - timedelta(days=DEFAULT_BACKFILL_DAYS)
                logger.info(f"No existing data found. Starting {DEFAULT_BACKFILL_DAYS}-day backfill from {start_date}")
            else:
                last_date = max(available_dates)
                start_date = last_date + timedelta(days=1)
                logger.info(f"Last data date: {last_date}. Backfilling from {start_date}")
                
            if start_date <= date.today():
                await self.manager.run_backfill(start_date, date.today())
            else:
                logger.info("Data is up to date. No backfill needed")
                
        except Exception as e:
            logger.error(f"Error during initial backfill: {e}")
            
    async def _daily_data_ingestion(self):
        try:
            today = date.today()
            
            if today.weekday() in MARKET_CLOSED_WEEKENDS:
                logger.info(f"Skipping data ingestion for {today} - market closed on weekends")
                return
                
            logger.info(f"Running daily data ingestion for {today}")
            result = await self.manager.run_daily_dump(today)
            
            if result.success:
                logger.info(f"Daily ingestion completed: {result.records_processed} records in {result.execution_time_seconds}s")
            else:
                logger.error(f"Daily ingestion failed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Critical error in daily data ingestion: {e}")
