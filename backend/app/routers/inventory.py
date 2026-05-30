from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from urllib.parse import quote

from ..database import get_db
from ..models import TransactionType
from ..schemas import (
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
from ..services.inventory import build_dashboard, create_transaction, delete_inventory_items, list_item_transactions, upsert_inventory_item


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/dashboard", response_model=InventoryDashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    return build_dashboard(db)


@router.get("/export-workbook")
def get_export_workbook(db: Session = Depends(get_db)):
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
async def post_import_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
def post_receipt(payload: InventoryTransactionCreate, db: Session = Depends(get_db)):
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
def post_issue(payload: InventoryTransactionCreate, db: Session = Depends(get_db)):
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
def post_manual_upsert(payload: InventoryManualUpsertRequest, db: Session = Depends(get_db)):
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
def get_item_transactions(item_id: int, db: Session = Depends(get_db)):
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
def post_bulk_delete(payload: InventoryBulkDeleteRequest, db: Session = Depends(get_db)):
    try:
        deleted_item_ids = delete_inventory_items(db, payload.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return InventoryBulkDeleteResponse(
        deleted_count=len(deleted_item_ids),
        deleted_item_ids=deleted_item_ids,
    )
