from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import SystemSetting
from ..schemas import FeishuSettingsRead, FeishuSettingsUpdateRequest


FEISHU_SETTING_KEYS = (
    "feishu_app_id",
    "feishu_app_secret",
    "feishu_purchase_approval_code",
)


@dataclass(frozen=True)
class FeishuRuntimeSettings:
    feishu_app_id: str | None
    feishu_app_secret: str | None
    feishu_purchase_approval_code: str | None


def _normalize_setting_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _read_db_settings(session: Session) -> dict[str, str | None]:
    rows = session.scalars(
        select(SystemSetting).where(SystemSetting.key.in_(FEISHU_SETTING_KEYS))
    ).all()
    return {row.key: _normalize_setting_value(row.value) for row in rows}


def get_effective_feishu_settings(session: Session) -> FeishuSettingsRead:
    settings = get_settings()
    db_values = _read_db_settings(session)
    return FeishuSettingsRead(
        feishu_app_id=db_values.get("feishu_app_id") or _normalize_setting_value(settings.feishu_app_id),
        feishu_app_secret=db_values.get("feishu_app_secret") or _normalize_setting_value(settings.feishu_app_secret),
        feishu_purchase_approval_code=db_values.get("feishu_purchase_approval_code")
        or _normalize_setting_value(settings.feishu_purchase_approval_code),
    )


def get_feishu_runtime_settings(session: Session) -> FeishuRuntimeSettings:
    effective = get_effective_feishu_settings(session)
    return FeishuRuntimeSettings(
        feishu_app_id=effective.feishu_app_id,
        feishu_app_secret=effective.feishu_app_secret,
        feishu_purchase_approval_code=effective.feishu_purchase_approval_code,
    )


def update_feishu_settings(
    session: Session,
    payload: FeishuSettingsUpdateRequest,
) -> FeishuSettingsRead:
    incoming = payload.model_dump()
    existing = {
        row.key: row
        for row in session.scalars(
            select(SystemSetting).where(SystemSetting.key.in_(FEISHU_SETTING_KEYS))
        ).all()
    }

    for key in FEISHU_SETTING_KEYS:
        normalized_value = _normalize_setting_value(incoming.get(key))
        row = existing.get(key)
        if row is None:
            row = SystemSetting(key=key, value=normalized_value)
            session.add(row)
            existing[key] = row
        else:
            row.value = normalized_value

    session.commit()
    return get_effective_feishu_settings(session)
