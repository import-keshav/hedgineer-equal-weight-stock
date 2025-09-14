import logging
from datetime import date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.constants import DAILY_CRON_HOUR, DAILY_CRON_MINUTE, MARKET_CLOSED_WEEKENDS, DEFAULT_BACKFILL_DAYS, TOP_COMPANIES_COUNT
from src.managers.index_data_dump_manager import IndexDataDumpManager
from src.managers.build_index_manager import BuildIndexManager

logger = logging.getLogger(__name__)


class CronScheduler:
    def __init__(self, index_data_dump_manager: IndexDataDumpManager, build_index_manager: BuildIndexManager):
        self.manager = index_data_dump_manager
        self.build_manager = build_index_manager
        self.scheduler = AsyncIOScheduler()
        
    async def start(self):
        logger.info("Starting cron scheduler")
        self._schedule_daily_job()
        self.scheduler.start()
        logger.info(f"Cron job scheduled for daily execution at {DAILY_CRON_HOUR:02d}:{DAILY_CRON_MINUTE:02d}")
        
        # Run initial backfill in background (non-blocking)
        self.scheduler.add_job(
            self._run_initial_backfill,
            'date',
            id='initial_backfill'
        )
        
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
            logger.info("Starting initial data backfill and index building...")
            
            available_dates = await self.manager.get_available_dates()
            
            if not available_dates:
                start_date = date.today() - timedelta(days=DEFAULT_BACKFILL_DAYS)
            else:
                last_date = max(available_dates)
                start_date = last_date + timedelta(days=1)
                if start_date > date.today():
                    start_date = date.today()
                
            await self.manager.run_backfill(start_date, date.today())
            
            index_start_date = date.today() - timedelta(days=DEFAULT_BACKFILL_DAYS)
            result = await self.build_manager.build_index(index_start_date, date.today())
            
            if result.success:
                logger.info(f"Index building completed: {result.total_compositions_built} compositions built")
            else:
                logger.error(f"Index building failed: {result.error_message}")
                
            logger.info("Initial setup completed! API endpoints are ready.")
                
        except Exception as e:
            logger.error(f"Error during initial backfill: {e}")
            
    async def _daily_data_ingestion(self):
        try:
            today = date.today()
            
            if today.weekday() in MARKET_CLOSED_WEEKENDS:
                return
                
            result = await self.manager.run_daily_dump(today)
            
            if result.success:
                logger.info(f"Daily ingestion completed: {result.records_processed} records")
            else:
                logger.error(f"Daily ingestion failed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Critical error in daily data ingestion: {e}")
