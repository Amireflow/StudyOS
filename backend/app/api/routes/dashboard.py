from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends
from app.api.deps import get_dashboard_service, get_utc_now
from app.core.security import get_current_user_id
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])


@router.get("", response_model=DashboardResponse, summary="Données agrégées du tableau de bord")
def read_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    now_utc: datetime = Depends(get_utc_now),
) -> DashboardResponse:
    return dashboard_service.get_dashboard(user_id, now_utc=now_utc)
