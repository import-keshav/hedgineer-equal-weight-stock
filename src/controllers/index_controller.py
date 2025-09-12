from datetime import date
from typing import Optional, List
from fastapi import APIRouter, FastAPI, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
from src.managers.index_manager import IndexManager
from src.managers.build_index_manager import BuildIndexManager
from src.dtos.index_result import IndexComposition, IndexPerformance, CompositionChange, IndexBuildResult


class BuildIndexRequest(BaseModel):
    start_date: date
    end_date: Optional[date] = None


class ExportDataRequest(BaseModel):
    start_date: date
    end_date: Optional[date] = None


class IndexController:
    def __init__(self, index_manager: IndexManager, build_index_manager: BuildIndexManager):
        self.index_manager = index_manager
        self.build_index_manager = build_index_manager
        self.router = APIRouter(tags=["Equal Weight Index"])
        self._setup_routes()
    
    def _setup_routes(self):
        @self.router.post("/build-index", response_model=IndexBuildResult)
        async def build_index(request: BuildIndexRequest):
            return await self.build_index_manager.build_index(request.start_date, request.end_date)
        
        @self.router.get("/index-performance", response_model=List[IndexPerformance])
        async def get_index_performance(
            start_date: date = Query(...),
            end_date: date = Query(...)
        ):
            return await self.index_manager.get_index_performance(start_date, end_date)
        
        @self.router.get("/index-composition", response_model=List[IndexComposition])
        async def get_index_composition(date: date = Query(...)):
            return await self.index_manager.get_index_composition(date)
        
        @self.router.get("/composition-changes", response_model=List[CompositionChange])
        async def get_composition_changes(
            start_date: date = Query(...),
            end_date: date = Query(...)
        ):
            return await self.index_manager.get_composition_changes(start_date, end_date)
        
        @self.router.post("/export-data")
        async def export_data(request: ExportDataRequest):
            excel_buffer = await self.index_manager.export_to_excel(request.start_date, request.end_date)
            excel_buffer.seek(0)
            return StreamingResponse(
                io.BytesIO(excel_buffer.read()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=index_data_{request.start_date}_{request.end_date or request.start_date}.xlsx"}
            )
    
    def register_routes(self, app: FastAPI):
        app.include_router(self.router)
