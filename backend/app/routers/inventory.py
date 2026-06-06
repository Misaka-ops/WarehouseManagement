from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from urllib.parse import quote

from ..auth import AuthUser, get_optional_current_user, require_authenticated_user
from ..database import get_db
from ..models import TransactionType
from ..schemas import (
    FinishedInventoryDashboardResponse,
    FinishedInventoryTransactionRead,
    InventoryBulkDeleteRequest,
    InventoryBulkDeleteResponse,
    InventoryDashboardResponse,
    InventoryImportResponse,
    InventoryItemRead,
    InventoryManualUpsertRequest,
    InventoryManualUpsertResponse,
    InventoryTransactionCreate,
    InventoryTransactionRead,
)
from ..services.bootstrap import export_warehouse_workbook, replace_inventory_from_warehouse_workbook
from ..services.finished_inventory import list_finished_inventory_items, list_finished_inventory_transactions
from ..services.inventory import build_dashboard, create_transaction, delete_inventory_items, list_item_transactions, upsert_inventory_item


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/dashboard", response_model=InventoryDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(get_optional_current_user),
):
    return build_dashboard(db, include_sensitive=current_user is not None)


@router.get("/finished-dashboard", response_model=FinishedInventoryDashboardResponse)
def get_finished_dashboard():
    try:
        return list_finished_inventory_items()
    except KeyError as exc:
        raise HTTPException(status_code=500, detail="Warehouse workbook is missing the '成品库存清单' sheet.") from exc


@router.get("/finished-items/{row_id}/transactions", response_model=list[FinishedInventoryTransactionRead])
def get_finished_item_transactions(row_id: int):
    try:
        return list_finished_inventory_transactions(row_id)
    except KeyError as exc:
        raise HTTPException(status_code=500, detail="Warehouse workbook is missing the '成品库存清单' sheet.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/export-workbook")
def get_export_workbook(
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    try:
        filename, workbook_bytes = export_warehouse_workbook(db)
    except KeyError as exc:
        raise HTTPException(status_code=500, detail="Warehouse workbook template is missing the required sheet.") from exc

    safe_filename = "warehouse-export.xlsx"
    content_disposition = f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{quote(filename)}"

    return StreamingResponse(
        BytesIO(workbook_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition},
    )


@router.post("/import-workbook", response_model=InventoryImportResponse)
async def post_import_workbook(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    filename = file.filename or "warehouse-workbook.xlsx"
    if not filename.lower().endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        raise HTTPException(status_code=400, detail="Only Excel .xlsx/.xlsm template files are supported.")

    workbook_bytes = await file.read()
    if not workbook_bytes:
        raise HTTPException(status_code=400, detail="Uploaded workbook is empty.")

    try:
        return replace_inventory_from_warehouse_workbook(
            db,
            workbook_bytes,
            workbook_name=filename,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="Workbook must contain the '原物料库存清单' sheet.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Workbook import failed. Please confirm the file uses the warehouse template.") from exc


@router.post("/receipt", response_model=InventoryTransactionRead)
def post_receipt(
    payload: InventoryTransactionCreate,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    try:
        transaction = create_transaction(db, transaction_type=TransactionType.receipt, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InventoryTransactionRead(
        id=transaction.id,
        item_id=transaction.item_id,
        transaction_type=transaction.transaction_type.value,
        quantity=transaction.quantity,
        occurred_on=transaction.occurred_on,
        operator_name=transaction.operator_name,
        reference_code=transaction.reference_code,
        notes=transaction.notes,
    )


@router.post("/issue", response_model=InventoryTransactionRead)
def post_issue(
    payload: InventoryTransactionCreate,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    try:
        transaction = create_transaction(db, transaction_type=TransactionType.issue, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InventoryTransactionRead(
        id=transaction.id,
        item_id=transaction.item_id,
        transaction_type=transaction.transaction_type.value,
        quantity=transaction.quantity,
        occurred_on=transaction.occurred_on,
        operator_name=transaction.operator_name,
        reference_code=transaction.reference_code,
        notes=transaction.notes,
    )


@router.post("/manual-upsert", response_model=InventoryManualUpsertResponse)
def post_manual_upsert(
    payload: InventoryManualUpsertRequest,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    try:
        item, transaction, created_item = upsert_inventory_item(db, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return InventoryManualUpsertResponse(
        created_item=created_item,
        item=InventoryItemRead.model_validate(item),
        transaction=InventoryTransactionRead(
            id=transaction.id,
            item_id=transaction.item_id,
            transaction_type=transaction.transaction_type.value,
            quantity=transaction.quantity,
            occurred_on=transaction.occurred_on,
            operator_name=transaction.operator_name,
            reference_code=transaction.reference_code,
            notes=transaction.notes,
        ),
    )


@router.get("/{item_id}/transactions", response_model=list[InventoryTransactionRead])
def get_item_transactions(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    transactions = list_item_transactions(db, item_id)
    return [
        InventoryTransactionRead(
            id=transaction.id,
            item_id=transaction.item_id,
            transaction_type=transaction.transaction_type.value,
            quantity=transaction.quantity,
            occurred_on=transaction.occurred_on,
            operator_name=transaction.operator_name,
            reference_code=transaction.reference_code,
            notes=transaction.notes,
        )
        for transaction in transactions
    ]


@router.post("/bulk-delete", response_model=InventoryBulkDeleteResponse)
def post_bulk_delete(
    payload: InventoryBulkDeleteRequest,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(require_authenticated_user),
):
    try:
        deleted_item_ids = delete_inventory_items(db, payload.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return InventoryBulkDeleteResponse(
        deleted_count=len(deleted_item_ids),
        deleted_item_ids=deleted_item_ids,
    )
