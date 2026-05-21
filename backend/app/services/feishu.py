from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    FeishuApprovalInstanceRecord,
    FeishuApprovalSyncState,
    FeishuPurchaseItemMeta,
    FeishuPurchaseOrderMeta,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from ..schemas import (
    FeishuApprovalDefinitionRead,
    FeishuApprovalInstanceRecordRead,
    FeishuApprovalSyncStateRead,
    FeishuPurchaseImportRequest,
    FeishuPurchaseImportResponse,
    FeishuInstancePullRequest,
    FeishuPurchaseSyncRequest,
    FeishuPurchaseSyncResponse,
)
from .bootstrap import normalize_text, to_date


class FeishuIntegrationError(RuntimeError):
    pass


@dataclass
class FeishuPage:
    payload: dict[str, Any]
    has_more: bool
    next_page_token: str | None


class FeishuClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._tenant_access_token: str | None = None

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 60,
        retries: int = 3,
    ) -> dict[str, Any]:
        request_headers = {
            "Accept": "application/json",
            "Connection": "close",
            "User-Agent": "WarehouseManagement/1.0",
        }
        if headers:
            request_headers.update(headers)

        data = None
        if json_body is not None:
            request_headers["Content-Type"] = "application/json; charset=utf-8"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")

        request = Request(url, data=data, headers=request_headers, method=method.upper())
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                with urlopen(request, timeout=timeout) as response:
                    raw = response.read().decode("utf-8")
                break
            except HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                raise FeishuIntegrationError(self._format_http_error(exc.code, raw)) from exc
            except URLError as exc:
                last_error = exc
                if attempt < retries and _is_transient_url_error(exc):
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise FeishuIntegrationError(f"飞书接口不可达: {exc.reason}") from exc
        else:
            if last_error is not None:
                raise FeishuIntegrationError(f"飞书接口不可达: {last_error.reason}") from last_error
            raise FeishuIntegrationError("飞书接口请求失败。")

        payload = self._parse_json(raw)
        if isinstance(payload, dict):
            code = payload.get("code")
            if code not in (None, 0):
                message = payload.get("msg") or payload.get("message") or payload.get("error") or "飞书接口返回错误"
                raise FeishuIntegrationError(f"{message} (code={code})")
            return payload
        return {"data": payload}

    @staticmethod
    def _parse_json(raw: str) -> Any:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    @staticmethod
    def _format_http_error(status_code: int, raw: str) -> str:
        parsed = FeishuClient._parse_json(raw)
        if isinstance(parsed, dict):
            message = parsed.get("msg") or parsed.get("message") or parsed.get("error") or raw or "飞书接口返回错误"
            code = parsed.get("code")
            if code is not None:
                return f"{message} (HTTP {status_code}, code={code})"
            return f"{message} (HTTP {status_code})"
        return f"飞书接口请求失败 (HTTP {status_code})"

    @property
    def tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token

        app_id = normalize_text(self.settings.feishu_app_id)
        app_secret = normalize_text(self.settings.feishu_app_secret)
        if not app_id or not app_secret:
            raise FeishuIntegrationError("缺少飞书 App ID 或 App Secret。")

        payload = self._request_json(
            "POST",
            f"{self.settings.feishu_open_api_base_url}/auth/v3/tenant_access_token/internal",
            json_body={"app_id": app_id, "app_secret": app_secret},
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        token = None
        if isinstance(data, dict):
            token = data.get("tenant_access_token")
        if not token:
            token = payload.get("tenant_access_token") if isinstance(payload, dict) else None
        if not token:
            raise FeishuIntegrationError("未能从飞书获取 tenant_access_token。")

        self._tenant_access_token = str(token)
        return self._tenant_access_token

    def _authorized_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tenant_access_token}"}

    def _request_candidates(
        self,
        method: str,
        urls: list[str],
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        query = f"?{urlencode({k: v for k, v in (params or {}).items() if v is not None})}" if params else ""
        for url in urls:
            try:
                return self._request_json(
                    method,
                    f"{url}{query}",
                    json_body=json_body,
                    headers=self._authorized_headers(),
                )
            except FeishuIntegrationError as exc:
                errors.append(str(exc))
        raise FeishuIntegrationError("；".join(errors) or "飞书接口请求失败。")

    def list_approval_instances(
        self,
        approval_code: str,
        *,
        page_size: int,
        page_token: str | None,
        instance_start_time_from: str | None = None,
        instance_start_time_to: str | None = None,
    ) -> FeishuPage:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        body: dict[str, Any] = {"approval_code": approval_code}
        if instance_start_time_from:
            body["instance_start_time_from"] = instance_start_time_from
        if instance_start_time_to:
            body["instance_start_time_to"] = instance_start_time_to
        payload = self._request_candidates(
            "POST",
            [f"{self.settings.feishu_open_api_base_url}/approval/v4/instances/query"],
            params=params,
            json_body=body,
        )
        data = payload.get("data") if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            data = payload if isinstance(payload, dict) else {}
        has_more = bool(data.get("has_more") or data.get("hasMore") or data.get("hasNext"))
        next_page_token = data.get("page_token") or data.get("next_page_token") or data.get("nextPageToken")
        return FeishuPage(payload=data, has_more=has_more, next_page_token=str(next_page_token) if next_page_token else None)

    def get_approval_instance(self, instance_code: str, *, locale: str) -> dict[str, Any]:
        payload = self._request_candidates(
            "GET",
            [f"{self.settings.feishu_open_api_base_url}/approval/v4/instances/{instance_code}"],
        )
        data = payload.get("data") if isinstance(payload, dict) else payload
        return data if isinstance(data, dict) else {"data": data}

    def get_approval_definition(self, approval_code: str, *, locale: str) -> dict[str, Any]:
        payload = self._request_candidates(
            "GET",
            [f"{self.settings.feishu_open_api_base_url}/approval/v4/approvals/{approval_code}"],
            params={"locale": locale},
        )
        data = payload.get("data") if isinstance(payload, dict) else payload
        return data if isinstance(data, dict) else {"data": data}


def _is_transient_url_error(exc: URLError) -> bool:
    reason = exc.reason
    if isinstance(reason, (ssl.SSLError, TimeoutError, ConnectionError, OSError)):
        return True
    text = str(reason)
    return "UNEXPECTED_EOF" in text or "EOF occurred in violation of protocol" in text or "timed out" in text.lower()


def _now() -> datetime:
    return datetime.utcnow()


def _normalize_code(value: str | None) -> str | None:
    return normalize_text(value)


def _parse_datetime_value(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds = seconds / 1000.0
        return datetime.fromtimestamp(seconds)

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        seconds = float(text)
        if seconds > 10_000_000_000:
            seconds = seconds / 1000.0
        return datetime.fromtimestamp(seconds)

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _first_present_value(payload: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if value not in (None, "", []):
                return value
        for value in payload.values():
            nested = _first_present_value(value, keys)
            if nested not in (None, "", []):
                return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _first_present_value(item, keys)
            if nested not in (None, "", []):
                return nested
    return None


def _extract_instance_code(payload: dict[str, Any]) -> str | None:
    for key in (
        "instance_code",
        "instanceCode",
        "approval_instance_code",
        "approvalInstanceCode",
        "code",
        "instance_id",
        "instanceId",
        "approval_instance_id",
        "approvalInstanceId",
    ):
        value = payload.get(key)
        if value not in (None, ""):
            return _normalize_code(str(value))

    for key in ("instance", "approval_instance", "approvalInstance", "data"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            for nested_key in (
                "instance_code",
                "instanceCode",
                "approval_instance_code",
                "approvalInstanceCode",
                "code",
                "instance_id",
                "instanceId",
            ):
                value = nested.get(nested_key)
                if value not in (None, ""):
                    return _normalize_code(str(value))

    return None


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_sources: list[Any] = []
    for key in ("items", "list", "instances", "instance_list", "approval_list", "records", "data"):
        value = payload.get(key)
        if value is not None:
            candidate_sources.append(value)
    if not candidate_sources:
        candidate_sources.append(payload)

    for source in candidate_sources:
        if isinstance(source, list):
            return [item for item in source if isinstance(item, dict)]
        if isinstance(source, dict):
            for key in ("items", "list", "instances", "instance_list", "approval_list", "records"):
                value = source.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
    return []


def _extract_instance_codes(payload: dict[str, Any], *, allowed_statuses: set[str] | None = None) -> list[str]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        data = payload if isinstance(payload, dict) else {}
    normalized_allowed_statuses = {status.strip().upper() for status in allowed_statuses} if allowed_statuses else None

    raw_list = data.get("instance_code_list")
    if isinstance(raw_list, list):
        codes: list[str] = []
        for item in raw_list:
            if isinstance(item, str) and item.strip():
                normalized = _normalize_code(item)
                if normalized and normalized not in codes:
                    codes.append(normalized)
            elif isinstance(item, dict):
                code = _extract_instance_code(item)
                if code and code not in codes:
                    codes.append(code)
        return codes

    raw_instance_list = data.get("instance_list")
    if isinstance(raw_instance_list, list):
        codes = []
        for item in raw_instance_list:
            if isinstance(item, str) and item.strip():
                normalized = _normalize_code(item)
                if normalized and normalized not in codes:
                    codes.append(normalized)
                continue
            if not isinstance(item, dict):
                continue
            if normalized_allowed_statuses is not None:
                status = _extract_status(item)
                if status is None or status.strip().upper() not in normalized_allowed_statuses:
                    continue
            nested_instance = item.get("instance")
            if isinstance(nested_instance, dict):
                code_value = nested_instance.get("code")
                if code_value not in (None, ""):
                    normalized = _normalize_code(str(code_value))
                    if normalized and normalized not in codes:
                        codes.append(normalized)
            code = _extract_instance_code(item)
            if code and code not in codes:
                codes.append(code)
        return codes

    codes: list[str] = []
    for item in _extract_items(payload):
        if normalized_allowed_statuses is not None:
            status = _extract_status(item)
            if status is None or status.strip().upper() not in normalized_allowed_statuses:
                continue
        code = _extract_instance_code(item)
        if code and code not in codes:
            codes.append(code)
    return codes


def _extract_title(payload: dict[str, Any]) -> str | None:
    return _normalize_code(
        _first_present_value(
            payload,
            (
                "title",
                "name",
                "approval_name",
                "approvalName",
                "summary",
                "subject",
            ),
        )
    )


def _extract_creator_name(payload: dict[str, Any]) -> str | None:
    value = _first_present_value(
        payload,
        (
            "creator_name",
            "creatorName",
            "originator_name",
            "originatorName",
            "start_user_name",
            "startUserName",
            "submitter_name",
            "submitterName",
            "user_name",
            "userName",
        ),
    )
    if value is not None:
        return _normalize_code(str(value))

    creator = _first_present_value(payload, ("creator", "originator", "submitter", "start_user"))
    if isinstance(creator, dict):
        nested = _first_present_value(creator, ("name", "user_name", "userName", "open_id", "union_id"))
        return _normalize_code(str(nested)) if nested is not None else None
    return None


def _extract_status(payload: dict[str, Any]) -> str | None:
    value = _first_present_value(
        payload,
        (
            "status",
            "approval_status",
            "approvalStatus",
            "instance_status",
            "instanceStatus",
            "state",
        ),
    )
    return _normalize_code(str(value)) if value is not None else None


def _extract_approval_name(payload: dict[str, Any]) -> str | None:
    value = _first_present_value(
        payload,
        (
            "approval_name",
            "approvalName",
            "name",
            "title",
        ),
    )
    return _normalize_code(str(value)) if value is not None else None


@dataclass
class ParsedFeishuPurchaseItem:
    line_no: int
    material_name: str
    specification: str | None
    requested_quantity: Decimal | None
    total_amount: Decimal | None
    link: str | None


@dataclass
class ParsedFeishuPurchaseOrder:
    requester: str | None
    purchase_category: str | None
    project_name: str | None
    purchase_channel: str | None
    department_name: str | None
    requested_at: date | None
    ordered_at: date | None
    contract_no: str | None
    notes: str | None
    serial_number: str | None
    approval_status: str | None
    title: str | None
    items: list[ParsedFeishuPurchaseItem]


def _parse_json_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def _parse_date_value(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    parsed = _parse_datetime_value(value)
    if parsed is not None:
        return parsed.date()
    return to_date(value)


def _coerce_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _parse_form_widgets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_form = payload.get("form")
    parsed = _parse_json_value(raw_form)
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        for key in ("value", "fields", "form", "items"):
            nested = parsed.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _widget_display_value(widget: dict[str, Any]) -> Any:
    value = widget.get("value")
    if value not in (None, ""):
        return value
    option = widget.get("option")
    if isinstance(option, dict):
        option_value = option.get("text") or option.get("value")
        if option_value not in (None, ""):
            return option_value
    return None


def _find_widget(widgets: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for widget in widgets:
        if normalize_text(widget.get("name")) == name:
            return widget
    return None


def _parse_item_rows(widgets: list[dict[str, Any]]) -> list[ParsedFeishuPurchaseItem]:
    item_widget = _find_widget(widgets, "物品明细")
    if not item_widget:
        return []

    raw_rows = item_widget.get("value")
    if not isinstance(raw_rows, list):
        return []

    rows: list[ParsedFeishuPurchaseItem] = []
    for index, raw_row in enumerate(raw_rows, start=1):
        if not isinstance(raw_row, list):
            continue

        row_widgets = [item for item in raw_row if isinstance(item, dict)]
        material_name = normalize_text(_widget_display_value(_find_widget(row_widgets, "名称") or {}))
        if not material_name:
            continue

        rows.append(
            ParsedFeishuPurchaseItem(
                line_no=index,
                material_name=material_name,
                specification=normalize_text(_widget_display_value(_find_widget(row_widgets, "规格") or {})),
                requested_quantity=_coerce_decimal(_widget_display_value(_find_widget(row_widgets, "数量") or {})),
                total_amount=_coerce_decimal(_widget_display_value(_find_widget(row_widgets, "金额") or {})),
                link=normalize_text(_widget_display_value(_find_widget(row_widgets, "链接（如需）") or {})),
            )
        )
    return rows


def _parse_feishu_purchase_payload(payload: dict[str, Any]) -> ParsedFeishuPurchaseOrder:
    widgets = _parse_form_widgets(payload)
    widget_map = {normalize_text(widget.get("name")): widget for widget in widgets if normalize_text(widget.get("name"))}

    requester = normalize_text(_widget_display_value(widget_map.get("请购人") or {}))
    purchase_category = normalize_text(_widget_display_value(widget_map.get("采购类别") or {}))
    project_name = normalize_text(_widget_display_value(widget_map.get("项目名称") or {}))
    purchase_channel = normalize_text(_widget_display_value(widget_map.get("采购渠道") or {}))
    department_name = normalize_text(_widget_display_value(widget_map.get("请购部门") or {}))
    requested_at = _parse_date_value(_widget_display_value(widget_map.get("需求时间") or {}))
    serial_number = normalize_text(payload.get("serial_number"))
    approval_status = _extract_status(payload)
    title = _extract_approval_name(payload)
    finished_at = _parse_datetime_value(
        _first_present_value(payload, ("finished_at", "finishedAt", "end_time", "endTime", "finish_time", "finishTime"))
    )
    contract_no = serial_number
    notes_parts = [part for part in (f"请购部门：{department_name}" if department_name else None, f"采购渠道：{purchase_channel}" if purchase_channel else None, normalize_text(_widget_display_value(widget_map.get("其它说明") or {}))) if part]
    notes = "；".join(notes_parts) if notes_parts else None
    items = _parse_item_rows(widgets)

    return ParsedFeishuPurchaseOrder(
        requester=requester,
        purchase_category=purchase_category,
        project_name=project_name,
        purchase_channel=purchase_channel,
        department_name=department_name,
        requested_at=requested_at,
        ordered_at=finished_at.date() if finished_at else requested_at,
        contract_no=contract_no,
        notes=notes,
        serial_number=serial_number,
        approval_status=approval_status,
        title=title,
        items=items,
    )


def _upsert_instance_record(session: Session, approval_code: str, payload: dict[str, Any]) -> tuple[FeishuApprovalInstanceRecord, bool]:
    instance_code = _extract_instance_code(payload)
    if not instance_code:
        raise FeishuIntegrationError("飞书审批实例缺少 instance_code。")

    record = session.scalar(
        select(FeishuApprovalInstanceRecord).where(FeishuApprovalInstanceRecord.instance_code == instance_code)
    )
    created = record is None
    if record is None:
        record = FeishuApprovalInstanceRecord(instance_code=instance_code, approval_code=approval_code, raw_payload="")
        session.add(record)

    record.approval_code = approval_code
    record.status = _extract_status(payload)
    record.title = _extract_title(payload)
    record.creator_name = _extract_creator_name(payload)
    record.started_at = _parse_datetime_value(
        _first_present_value(payload, ("started_at", "startedAt", "start_time", "startTime", "create_time", "createTime"))
    )
    record.finished_at = _parse_datetime_value(
        _first_present_value(payload, ("finished_at", "finishedAt", "end_time", "endTime", "finish_time", "finishTime"))
    )
    record.raw_payload = json.dumps(payload, ensure_ascii=False, default=str)
    return record, created


def _get_or_create_sync_state(session: Session, approval_code: str) -> FeishuApprovalSyncState:
    state = session.scalar(
        select(FeishuApprovalSyncState).where(FeishuApprovalSyncState.approval_code == approval_code)
    )
    if state is None:
        state = FeishuApprovalSyncState(approval_code=approval_code)
        session.add(state)
    return state


def _resolve_time_window(days: int | None) -> tuple[str | None, str | None]:
    if days is None:
        return None, None
    if days not in {1, 5, 10}:
        raise FeishuIntegrationError("仅支持近一天、近五天、近十天的同步范围。")

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    return str(int(start_time.timestamp() * 1000)), str(int(end_time.timestamp() * 1000))


def _fetch_instance_detail_with_retry(
    client: FeishuClient,
    instance_code: str,
    *,
    locale: str,
    retries: int = 3,
) -> dict[str, Any]:
    last_error: FeishuIntegrationError | None = None
    for attempt in range(retries + 1):
        try:
            return client.get_approval_instance(instance_code, locale=locale)
        except FeishuIntegrationError as exc:
            last_error = exc
            message = str(exc)
            transient = "UNEXPECTED_EOF_WHILE_READING" in message or "EOF occurred in violation of protocol" in message
            if attempt >= retries or not transient:
                break
            time.sleep(0.75 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise FeishuIntegrationError(f"{instance_code}: 飞书实例详情获取失败。")


def serialize_feishu_instance(record: FeishuApprovalInstanceRecord) -> FeishuApprovalInstanceRecordRead:
    return FeishuApprovalInstanceRecordRead.model_validate(record)


def serialize_feishu_sync_state(state: FeishuApprovalSyncState) -> FeishuApprovalSyncStateRead:
    return FeishuApprovalSyncStateRead.model_validate(state)


def get_feishu_approval_definition(
    approval_code: str | None = None,
    *,
    locale: str = "zh-CN",
) -> FeishuApprovalDefinitionRead:
    settings = get_settings()
    resolved_code = _normalize_code(approval_code) or _normalize_code(settings.feishu_purchase_approval_code)
    if not resolved_code:
        raise FeishuIntegrationError("请先配置飞书采购审批编码，或传入 approval_code。")

    client = FeishuClient()
    payload = client.get_approval_definition(resolved_code, locale=locale)
    return FeishuApprovalDefinitionRead(
        approval_code=resolved_code,
        approval_name=_extract_approval_name(payload),
        status=_extract_status(payload),
        raw_payload=json.dumps(payload, ensure_ascii=False, default=str),
    )


def list_feishu_instance_records(
    session: Session,
    *,
    approval_code: str | None = None,
    limit: int = 50,
) -> list[FeishuApprovalInstanceRecordRead]:
    statement = select(FeishuApprovalInstanceRecord).order_by(
        FeishuApprovalInstanceRecord.updated_at.desc().nullslast(),
        FeishuApprovalInstanceRecord.id.desc(),
    )
    if approval_code:
        statement = statement.where(FeishuApprovalInstanceRecord.approval_code == approval_code)
    records = session.scalars(statement.limit(limit)).all()
    return [serialize_feishu_instance(record) for record in records]


def list_feishu_sync_states(
    session: Session,
    *,
    approval_code: str | None = None,
) -> list[FeishuApprovalSyncStateRead]:
    statement = select(FeishuApprovalSyncState).order_by(
        FeishuApprovalSyncState.updated_at.desc().nullslast(),
        FeishuApprovalSyncState.id.desc(),
    )
    if approval_code:
        statement = statement.where(FeishuApprovalSyncState.approval_code == approval_code)
    states = session.scalars(statement).all()
    return [serialize_feishu_sync_state(state) for state in states]


def sync_feishu_purchase_instances(
    session: Session,
    payload: FeishuPurchaseSyncRequest,
) -> FeishuPurchaseSyncResponse:
    settings = get_settings()
    approval_code = _normalize_code(payload.approval_code) or _normalize_code(settings.feishu_purchase_approval_code)
    if not approval_code:
        raise FeishuIntegrationError("请先配置飞书采购审批编码，或在请求体中传入 approval_code。")

    client = FeishuClient()
    client.tenant_access_token
    warnings: list[str] = []
    instance_codes: list[str] = []
    start_time, end_time = _resolve_time_window(payload.time_range_days)

    if payload.instance_codes:
        for code in payload.instance_codes:
            normalized = _normalize_code(code)
            if normalized and normalized not in instance_codes:
                instance_codes.append(normalized)
    else:
        page_token: str | None = None
        for _ in range(payload.max_pages):
            page = client.list_approval_instances(
                approval_code,
                page_size=payload.page_size,
                page_token=page_token,
                instance_start_time_from=start_time,
                instance_start_time_to=end_time,
            )
            for instance_code in _extract_instance_codes(page.payload, allowed_statuses={"APPROVED", "PASSED", "DONE", "COMPLETED", "SUCCESS"}):
                if instance_code and instance_code not in instance_codes:
                    instance_codes.append(instance_code)
            if not page.has_more or not page.next_page_token:
                break
            page_token = page.next_page_token

    created_count = 0
    updated_count = 0
    last_synced_instance_code: str | None = None
    records: list[FeishuApprovalInstanceRecord] = []
    detail_payloads: dict[str, dict[str, Any]] = {}
    created_instance_codes: set[str] = set()
    apply_historical_filter = False
    apply_imported_filter = False

    if instance_codes:
        worker_count = min(8, len(instance_codes))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(_fetch_instance_detail_with_retry, client, instance_code, locale=payload.locale): instance_code
                for instance_code in instance_codes
            }
            for future in as_completed(future_map):
                instance_code = future_map[future]
                try:
                    detail_payloads[instance_code] = future.result()
                except FeishuIntegrationError as exc:
                    warnings.append(f"{instance_code}: {exc}")

    for instance_code in instance_codes:
        detail_payload = detail_payloads.get(instance_code)
        if detail_payload is None:
            continue
        record, created = _upsert_instance_record(session, approval_code, detail_payload)
        records.append(record)
        last_synced_instance_code = instance_code
        if created:
            created_count += 1
            created_instance_codes.add(instance_code)
        else:
            updated_count += 1

    historical_instance_codes = {record.instance_code for record in records if record.instance_code not in created_instance_codes}
    imported_instance_codes: set[str] = set()
    if records:
        imported_instance_codes = set(
            session.scalars(
                select(FeishuPurchaseOrderMeta.approval_instance_code).where(
                    FeishuPurchaseOrderMeta.approval_code == approval_code,
                    FeishuPurchaseOrderMeta.approval_instance_code.in_([record.instance_code for record in records]),
                )
            ).all()
        )

    sync_state = _get_or_create_sync_state(session, approval_code)
    sync_state.last_synced_at = _now()
    sync_state.last_synced_instance_code = last_synced_instance_code
    sync_state.last_sync_status = "success_with_warnings" if warnings else ("success" if instance_codes else "empty")
    sync_state.last_sync_message = (
        f"同步完成，抓取 {len(instance_codes)} 条实例，新增 {created_count} 条，更新 {updated_count} 条。"
        + (" 强制重跑模式已开启。" if payload.force_reimport else "")
        + (f" 警告：{'；'.join(warnings[:5])}" if warnings else "")
    )

    session.commit()

    refreshed_state = session.scalar(
        select(FeishuApprovalSyncState).where(FeishuApprovalSyncState.approval_code == approval_code)
    )
    if refreshed_state is None:
        raise FeishuIntegrationError("飞书同步状态保存失败。")

    refreshed_records = session.scalars(
        select(FeishuApprovalInstanceRecord)
        .where(FeishuApprovalInstanceRecord.instance_code.in_([record.instance_code for record in records]))
        .order_by(FeishuApprovalInstanceRecord.updated_at.desc().nullslast(), FeishuApprovalInstanceRecord.id.desc())
    ).all()

    return FeishuPurchaseSyncResponse(
        approval_code=approval_code,
        fetched_instance_count=len(instance_codes),
        created_instance_count=created_count,
        updated_instance_count=updated_count,
        skipped_instance_count=max(len(instance_codes) - created_count - updated_count, 0),
        filtered_imported_instance_count=len(imported_instance_codes),
        filtered_historical_instance_count=len(historical_instance_codes),
        sync_state=serialize_feishu_sync_state(refreshed_state),
        instances=[serialize_feishu_instance(record) for record in refreshed_records],
        warnings=warnings,
    )


def _is_approved_instance(status: str | None) -> bool:
    if not status:
        return False
    normalized = status.strip().upper()
    return normalized in {"APPROVED", "PASSED", "DONE", "COMPLETED", "SUCCESS"}


def _match_inventory_item(session: Session, material_name: str, specification: str | None) -> InventoryItem | None:
    return session.scalar(
        select(InventoryItem)
        .where(
            InventoryItem.material_name == material_name,
            InventoryItem.specification == specification,
        )
        .order_by(InventoryItem.id.asc())
    )


def _build_purchase_order_notes(parsed: ParsedFeishuPurchaseOrder, approval_code: str, instance_code: str) -> str | None:
    source_bits = [f"飞书来源：{approval_code}", f"实例：{instance_code}"]
    if parsed.notes:
        source_bits.append(parsed.notes)
    return "；".join(source_bits) if source_bits else None


def _purge_feishu_purchase_order(session: Session, instance_code: str) -> bool:
    existing_meta = session.scalar(
        select(FeishuPurchaseOrderMeta).where(FeishuPurchaseOrderMeta.approval_instance_code == instance_code)
    )
    if existing_meta is None or existing_meta.purchase_order is None:
        return False

    if any((item.received_quantity or Decimal("0")) > 0 for item in existing_meta.purchase_order.items):
        raise FeishuIntegrationError(f"{instance_code}: 该采购单已发生收货，禁止强制重跑。")

    session.delete(existing_meta.purchase_order)
    session.flush()
    return True


def _import_feishu_purchase_instance(
    session: Session,
    *,
    approval_code: str,
    instance_record: FeishuApprovalInstanceRecord,
) -> tuple[int, int, bool]:
    if not _is_approved_instance(instance_record.status):
        return 0, 0, False

    existing_meta = session.scalar(
        select(FeishuPurchaseOrderMeta).where(FeishuPurchaseOrderMeta.approval_instance_code == instance_record.instance_code)
    )
    if existing_meta is not None:
        return 0, 0, False

    try:
        payload = json.loads(instance_record.raw_payload)
    except json.JSONDecodeError as exc:
        raise FeishuIntegrationError(f"{instance_record.instance_code}: 飞书实例原始数据不可解析。") from exc

    if not isinstance(payload, dict):
        raise FeishuIntegrationError(f"{instance_record.instance_code}: 飞书实例原始数据格式不正确。")

    parsed = _parse_feishu_purchase_payload(payload)
    if not parsed.items:
        raise FeishuIntegrationError(f"{instance_record.instance_code}: 未能从飞书表单解析出采购明细。")

    order = PurchaseOrder(
        sheet_name="飞书采购申请",
        requester=parsed.requester,
        purchase_category=parsed.purchase_category,
        project_name=parsed.project_name,
        supplier_name=None,
        status=PurchaseOrderStatus.pending,
        requested_at=parsed.requested_at,
        ordered_at=parsed.ordered_at,
        contract_no=parsed.contract_no,
        notes=_build_purchase_order_notes(parsed, approval_code, instance_record.instance_code),
    )
    session.add(order)
    session.flush()

    session.add(
        FeishuPurchaseOrderMeta(
            approval_instance_code=instance_record.instance_code,
            approval_code=approval_code,
            purchase_order_id=order.id,
            serial_number=parsed.serial_number,
            approval_status=parsed.approval_status,
        )
    )

    imported_item_count = 0
    for row in parsed.items:
        inventory_item = _match_inventory_item(session, row.material_name, row.specification)
        purchase_item = PurchaseOrderItem(
            order_id=order.id,
            inventory_item_id=inventory_item.id if inventory_item else None,
            line_no=row.line_no,
            material_name=row.material_name,
            specification=row.specification,
            requested_quantity=row.requested_quantity,
            received_quantity=Decimal("0"),
            unit=None,
            unit_price=None,
            tax_rate=None,
            total_amount=row.total_amount,
            expected_arrival=parsed.requested_at,
        )
        session.add(purchase_item)
        session.flush()
        session.add(
            FeishuPurchaseItemMeta(
                purchase_item_id=purchase_item.id,
                approval_instance_code=instance_record.instance_code,
                source_line_no=row.line_no,
            )
        )
        imported_item_count += 1

    return 1, imported_item_count, True


def pull_feishu_instance_by_code(
    session: Session,
    payload: FeishuInstancePullRequest,
) -> FeishuApprovalInstanceRecordRead:
    settings = get_settings()
    approval_code = _normalize_code(payload.approval_code) or _normalize_code(settings.feishu_purchase_approval_code)
    if not approval_code:
        raise FeishuIntegrationError("请先配置飞书采购审批编码，或在请求体中传入 approval_code。")

    instance_code = _normalize_code(payload.instance_code)
    if not instance_code:
        raise FeishuIntegrationError("instance_code 不能为空。")

    client = FeishuClient()
    detail_payload = client.get_approval_instance(instance_code, locale=payload.locale)
    record, _ = _upsert_instance_record(session, approval_code, detail_payload)
    session.commit()
    session.refresh(record)
    return serialize_feishu_instance(record)


def import_feishu_purchase_instances(
    session: Session,
    payload: FeishuPurchaseImportRequest,
) -> FeishuPurchaseImportResponse:
    sync_response = sync_feishu_purchase_instances(session, payload)
    imported_order_count = 0
    imported_item_count = 0
    reimported_order_count = 0
    reimported_item_count = 0
    skipped_import_count = 0
    warnings = list(sync_response.warnings)
    force_reimport = bool(payload.force_reimport)

    for record in sync_response.instances:
        if not _is_approved_instance(record.status):
            skipped_import_count += 1
            continue

        existing_meta = session.scalar(
            select(FeishuPurchaseOrderMeta).where(FeishuPurchaseOrderMeta.approval_instance_code == record.instance_code)
        )
        if existing_meta is not None and force_reimport:
            try:
                _purge_feishu_purchase_order(session, record.instance_code)
            except FeishuIntegrationError as exc:
                skipped_import_count += 1
                warnings.append(str(exc))
                continue
        elif existing_meta is not None:
            skipped_import_count += 1
            continue

        try:
            payload_dict = json.loads(record.raw_payload)
            if not isinstance(payload_dict, dict):
                raise FeishuIntegrationError(f"{record.instance_code}: 飞书实例原始数据格式不正确。")
            parsed = _parse_feishu_purchase_payload(payload_dict)
            if not parsed.items:
                raise FeishuIntegrationError(f"{record.instance_code}: 未能从飞书表单解析出采购明细。")

            order = PurchaseOrder(
                sheet_name="飞书采购申请",
                requester=parsed.requester,
                purchase_category=parsed.purchase_category,
                project_name=parsed.project_name,
                supplier_name=None,
                status=PurchaseOrderStatus.pending,
                requested_at=parsed.requested_at,
                ordered_at=parsed.ordered_at,
                contract_no=parsed.contract_no,
                notes=_build_purchase_order_notes(parsed, sync_response.approval_code, record.instance_code),
            )
            session.add(order)
            session.flush()

            session.add(
                FeishuPurchaseOrderMeta(
                    approval_instance_code=record.instance_code,
                    approval_code=sync_response.approval_code,
                    purchase_order_id=order.id,
                    serial_number=parsed.serial_number,
                    approval_status=parsed.approval_status,
                )
            )

            if existing_meta is not None and force_reimport:
                reimported_order_count += 1
            else:
                imported_order_count += 1
            for row in parsed.items:
                inventory_item = _match_inventory_item(session, row.material_name, row.specification)
                purchase_item = PurchaseOrderItem(
                    order_id=order.id,
                    inventory_item_id=inventory_item.id if inventory_item else None,
                    line_no=row.line_no,
                    material_name=row.material_name,
                    specification=row.specification,
                    requested_quantity=row.requested_quantity,
                    received_quantity=Decimal("0"),
                    unit=None,
                    unit_price=None,
                    tax_rate=None,
                    total_amount=row.total_amount,
                    expected_arrival=parsed.requested_at,
                )
                session.add(purchase_item)
                session.flush()
                session.add(
                    FeishuPurchaseItemMeta(
                        purchase_item_id=purchase_item.id,
                        approval_instance_code=record.instance_code,
                        source_line_no=row.line_no,
                    )
                )
                if existing_meta is not None and force_reimport:
                    reimported_item_count += 1
                else:
                    imported_item_count += 1
        except FeishuIntegrationError as exc:
            skipped_import_count += 1
            warnings.append(str(exc))

    session.commit()

    return FeishuPurchaseImportResponse(
        approval_code=sync_response.approval_code,
        fetched_instance_count=sync_response.fetched_instance_count,
        created_instance_count=sync_response.created_instance_count,
        updated_instance_count=sync_response.updated_instance_count,
        reimported_order_count=reimported_order_count,
        reimported_item_count=reimported_item_count,
        imported_order_count=imported_order_count,
        imported_item_count=imported_item_count,
        skipped_instance_count=sync_response.skipped_instance_count,
        skipped_import_count=skipped_import_count,
        filtered_imported_instance_count=sync_response.filtered_imported_instance_count,
        filtered_historical_instance_count=sync_response.filtered_historical_instance_count,
        sync_state=sync_response.sync_state,
        instances=sync_response.instances,
        warnings=warnings,
    )
