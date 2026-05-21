from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.feishu import FeishuClient, _extract_instance_codes  # noqa: E402


@dataclass(frozen=True)
class Variant:
    name: str
    params_keys: tuple[str, ...]
    body_keys: tuple[str, ...]
    use_milliseconds: bool


VARIANTS: tuple[Variant, ...] = (
    Variant(
        name="current_body_ms",
        params_keys=(),
        body_keys=("instance_start_time_from", "instance_start_time_to"),
        use_milliseconds=True,
    ),
    Variant(
        name="current_body_sec",
        params_keys=(),
        body_keys=("instance_start_time_from", "instance_start_time_to"),
        use_milliseconds=False,
    ),
    Variant(
        name="query_ms",
        params_keys=("instance_start_time_from", "instance_start_time_to"),
        body_keys=(),
        use_milliseconds=True,
    ),
    Variant(
        name="query_sec",
        params_keys=("instance_start_time_from", "instance_start_time_to"),
        body_keys=(),
        use_milliseconds=False,
    ),
    Variant(
        name="legacy_body_ms",
        params_keys=(),
        body_keys=("start_time", "end_time"),
        use_milliseconds=True,
    ),
    Variant(
        name="legacy_body_sec",
        params_keys=(),
        body_keys=("start_time", "end_time"),
        use_milliseconds=False,
    ),
)


def build_window(days: int, *, use_milliseconds: bool) -> tuple[str, str]:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    factor = 1000 if use_milliseconds else 1
    return str(int(start_time.timestamp() * factor)), str(int(end_time.timestamp() * factor))


def request_variant(client: FeishuClient, approval_code: str, days: int, variant: Variant) -> dict[str, Any]:
    start_time, end_time = build_window(days, use_milliseconds=variant.use_milliseconds)
    params: dict[str, Any] = {"page_size": 100}
    body: dict[str, Any] = {"approval_code": approval_code}

    for key in variant.params_keys:
        params[key] = start_time if key.endswith("_from") or key == "start_time" else end_time
    for key in variant.body_keys:
        body[key] = start_time if key.endswith("_from") or key == "start_time" else end_time

    payload = client._request_candidates(  # noqa: SLF001
        "POST",
        [f"{client.settings.feishu_open_api_base_url}/approval/v4/instances/query"],
        params=params,
        json_body=body,
    )
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = payload if isinstance(payload, dict) else {}

    instance_codes = _extract_instance_codes(payload if isinstance(payload, dict) else {})
    return {
        "instance_count": len(instance_codes),
        "instance_codes_preview": instance_codes[:10],
        "has_more": bool(data.get("has_more") or data.get("hasMore") or data.get("hasNext")),
        "next_page_token": data.get("page_token") or data.get("next_page_token") or data.get("nextPageToken"),
        "request_start": start_time,
        "request_end": end_time,
    }


def main() -> int:
    settings = get_settings()
    approval_code = (settings.feishu_purchase_approval_code or "").strip()
    if not approval_code:
        print("Missing FEISHU_PURCHASE_APPROVAL_CODE", file=sys.stderr)
        return 1

    client = FeishuClient()
    report: dict[str, Any] = {"approval_code": approval_code, "results": {}}

    for days in (1, 5, 10):
        day_key = f"{days}_days"
        report["results"][day_key] = {}
        for variant in VARIANTS:
            try:
                report["results"][day_key][variant.name] = request_variant(client, approval_code, days, variant)
            except Exception as exc:  # noqa: BLE001
                report["results"][day_key][variant.name] = {"error": str(exc)}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
