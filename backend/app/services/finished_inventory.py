from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from ..config import get_settings
from ..schemas import (
    FinishedInventoryDashboardResponse,
    FinishedInventoryItemRead,
    FinishedInventorySummary,
    FinishedInventoryTransactionRead,
)
from .bootstrap import normalize_text, to_date


FINISHED_SHEET_NAME = "成品库存清单"
LOW_STOCK_THRESHOLD = Decimal("5")


@dataclass(frozen=True)
class FinishedInventoryRow:
    row_id: int
    material_name: str
    specification: str | None
    work_order_no: str | None
    quantity_on_hand: Decimal
    unit: str | None
    location_name: str | None
    receipt_date: date | None
    receipt_quantity: Decimal
    notes: str | None
    issue_quantity_1: Decimal
    issue_date_1: date | None
    issue_operator_1: str | None
    issue_quantity_2: Decimal
    issue_date_2: date | None
    issue_operator_2: str | None
    issue_quantity_3: Decimal
    issue_date_3: date | None
    issue_operator_3: str | None
    project_code: str | None
    producer_name: str | None
    customer_name: str | None


def _to_decimal(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")

    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError):
        return Decimal("0")


def _to_finished_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float, Decimal)):
        try:
            converted = from_excel(float(value))
        except (TypeError, ValueError, OverflowError):
            return None
        if isinstance(converted, datetime):
            return converted.date()
        if isinstance(converted, date):
            return converted
        return None
    return to_date(value)


def _load_finished_rows() -> list[FinishedInventoryRow]:
    settings = get_settings()
    workbook_path = settings.warehouse_workbook
    workbook = load_workbook(workbook_path, data_only=True, read_only=True)

    if FINISHED_SHEET_NAME not in workbook.sheetnames:
        raise KeyError(FINISHED_SHEET_NAME)

    sheet = workbook[FINISHED_SHEET_NAME]
    rows: list[FinishedInventoryRow] = []

    for row_id, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        material_name = normalize_text(row[1] if len(row) > 1 else None)
        if not material_name:
            continue

        rows.append(
            FinishedInventoryRow(
                row_id=row_id,
                material_name=material_name,
                specification=normalize_text(row[2] if len(row) > 2 else None),
                work_order_no=normalize_text(row[3] if len(row) > 3 else None),
                quantity_on_hand=_to_decimal(row[4] if len(row) > 4 else None),
                unit=normalize_text(row[5] if len(row) > 5 else None),
                location_name=normalize_text(row[6] if len(row) > 6 else None),
                receipt_date=_to_finished_date(row[7] if len(row) > 7 else None),
                receipt_quantity=_to_decimal(row[8] if len(row) > 8 else None),
                notes=normalize_text(row[9] if len(row) > 9 else None),
                issue_quantity_1=_to_decimal(row[10] if len(row) > 10 else None),
                issue_date_1=_to_finished_date(row[11] if len(row) > 11 else None),
                issue_operator_1=normalize_text(row[12] if len(row) > 12 else None),
                issue_quantity_2=_to_decimal(row[13] if len(row) > 13 else None),
                issue_date_2=_to_finished_date(row[14] if len(row) > 14 else None),
                issue_operator_2=normalize_text(row[15] if len(row) > 15 else None),
                issue_quantity_3=_to_decimal(row[16] if len(row) > 16 else None),
                issue_date_3=_to_finished_date(row[17] if len(row) > 17 else None),
                issue_operator_3=normalize_text(row[18] if len(row) > 18 else None),
                project_code=normalize_text(row[19] if len(row) > 19 else None),
                producer_name=normalize_text(row[20] if len(row) > 20 else None),
                customer_name=normalize_text(row[21] if len(row) > 21 else None),
            )
        )

    return rows


def _build_finished_item(row: FinishedInventoryRow) -> FinishedInventoryItemRead:
    issue_dates = [row.issue_date_1, row.issue_date_2, row.issue_date_3]
    return FinishedInventoryItemRead(
        row_id=row.row_id,
        material_name=row.material_name,
        specification=row.specification,
        work_order_no=row.work_order_no,
        quantity_on_hand=row.quantity_on_hand,
        unit=row.unit,
        location_name=row.location_name,
        project_code=row.project_code,
        producer_name=row.producer_name,
        customer_name=row.customer_name,
        notes=row.notes,
        last_receipt_at=row.receipt_date,
        last_issue_at=max((value for value in issue_dates if value is not None), default=None),
    )


def list_finished_inventory_items() -> FinishedInventoryDashboardResponse:
    rows = _load_finished_rows()
    items = [_build_finished_item(row) for row in rows]
    total_stock_quantity = sum((item.quantity_on_hand for item in items), start=Decimal("0"))
    low_stock_items = sum(1 for item in items if item.quantity_on_hand <= LOW_STOCK_THRESHOLD)

    return FinishedInventoryDashboardResponse(
        summary=FinishedInventorySummary(
            total_items=len(items),
            total_stock_quantity=total_stock_quantity,
            low_stock_items=low_stock_items,
        ),
        items=items,
    )


def list_finished_inventory_transactions(row_id: int) -> list[FinishedInventoryTransactionRead]:
    rows = _load_finished_rows()
    target = next((row for row in rows if row.row_id == row_id), None)
    if target is None:
        raise ValueError("Finished inventory row not found.")

    transactions: list[FinishedInventoryTransactionRead] = []

    if target.receipt_quantity > 0 or target.receipt_date is not None:
        transactions.append(
            FinishedInventoryTransactionRead(
                id=f"{row_id}-receipt",
                row_id=row_id,
                transaction_type="receipt",
                quantity=target.receipt_quantity,
                occurred_on=target.receipt_date,
                notes=target.notes or "由成品库存清单派生的最近入库记录",
            )
        )

    issue_slots = [
        (1, target.issue_quantity_1, target.issue_date_1, target.issue_operator_1),
        (2, target.issue_quantity_2, target.issue_date_2, target.issue_operator_2),
        (3, target.issue_quantity_3, target.issue_date_3, target.issue_operator_3),
    ]
    for slot, quantity, occurred_on, operator_name in issue_slots:
        if quantity <= 0 and occurred_on is None and operator_name is None:
            continue
        transactions.append(
            FinishedInventoryTransactionRead(
                id=f"{row_id}-issue-{slot}",
                row_id=row_id,
                transaction_type="issue",
                quantity=quantity,
                occurred_on=occurred_on,
                operator_name=operator_name,
                notes=f"由成品库存清单派生的出库记录 {slot}",
            )
        )

    transactions.sort(
        key=lambda item: (
            item.occurred_on or date.min,
            1 if item.transaction_type == "receipt" else 0,
            item.id,
        ),
        reverse=True,
    )
    return transactions
