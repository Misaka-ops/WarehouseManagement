from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_authenticated_user
from ..database import get_db
from ..schemas import FeishuSettingsRead, FeishuSettingsUpdateRequest
from ..services.system_settings import get_effective_feishu_settings, update_feishu_settings


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/feishu", response_model=FeishuSettingsRead)
def get_feishu_settings(db: Session = Depends(get_db)):
    return get_effective_feishu_settings(db)


@router.put("/feishu", response_model=FeishuSettingsRead)
def put_feishu_settings(payload: FeishuSettingsUpdateRequest, db: Session = Depends(get_db)):
    return update_feishu_settings(db, payload)
