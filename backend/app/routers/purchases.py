from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import PurchaseOrder
from ..schemas import (
    InventoryTransactionRead,
    PurchaseImportedItemsAdjustRequest,
    PurchaseImportedItemsAdjustResponse,
    PurchaseImportResponse,
    PurchaseImportStateRead,
    PurchasePendingReceiptDeleteRequest,
    PurchasePendingReceiptDeleteResponse,
    PurchaseImportStateUpdateRequest,
    PurchaseOrderRead,
    PurchaseReceiveCandidate,
    PurchaseReceiveCreate,
)
from ..services.inventory import list_pending_purchase_receipts, receive_purchase_item
from ..services.purchases import (
    delete_pending_purchase_items,
    get_or_create_purchase_import_states,
    import_purchase_workbook_incremental,
    serialize_purchase_import_state,
    update_imported_purchase_items,
    update_purchase_import_states,
)


router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("/import-states", response_model=list[PurchaseImportStateRead])
def get_import_states(db: Session = Depends(get_db)):
    return [serialize_purchase_import_state(state) for state in get_or_create_purchase_import_states(db)]


@router.patch("/import-states", response_model=list[PurchaseImportStateRead])
def patch_import_states(payload: PurchaseImportStateUpdateRequest, db: Session = Depends(get_db)):
    try:
        return update_purchase_import_states(
            db,
            [{"sheet_name": item.sheet_name, "last_imported_row": item.last_imported_row} for item in payload.states],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-workbook", response_model=PurchaseImportResponse)
async def post_import_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "purchase-workbook.xlsx"
    if not filename.lower().endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        raise HTTPException(status_code=400, detail="Only Excel .xlsx/.xlsm template files are supported.")

    workbook_bytes = await file.read()
    if not workbook_bytes:
        raise HTTPException(status_code=400, detail="Uploaded workbook is empty.")

    try:
        return import_purchase_workbook_incremental(
            db,
            workbook_bytes,
            workbook_name=filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Purchase workbook import failed. Please confirm the file uses the current template.") from exc


@router.patch("/imported-items", response_model=PurchaseImportedItemsAdjustResponse)
def patch_imported_items(payload: PurchaseImportedItemsAdjustRequest, db: Session = Depends(get_db)):
    try:
        items = update_imported_purchase_items(db, payload.items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PurchaseImportedItemsAdjustResponse(
        updated_item_count=len(items),
        items=items,
    )


@router.get("", response_model=list[PurchaseOrderRead])
def list_purchase_orders(db: Session = Depends(get_db)):
    orders = db.scalars(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .order_by(PurchaseOrder.ordered_at.desc().nullslast(), PurchaseOrder.id.desc())
    ).all()
    return [
        PurchaseOrderRead(
            id=order.id,
            sheet_name=order.sheet_name,
            requester=order.requester,
            purchase_category=order.purchase_category,
            project_name=order.project_name,
            supplier_name=order.supplier_name,
            status=order.status.value,
            requested_at=order.requested_at,
            ordered_at=order.ordered_at,
            contract_no=order.contract_no,
            notes=order.notes,
            items=[
                {
                    "id": item.id,
                    "line_no": item.line_no,
                    "material_name": item.material_name,
                    "specification": item.specification,
                    "requested_quantity": item.requested_quantity,
                    "received_quantity": item.received_quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "total_amount": item.total_amount,
                    "expected_arrival": item.expected_arrival,
                    "pending_quantity": (item.requested_quantity or 0) - (item.received_quantity or 0),
                }
                for item in order.items
            ],
        )
        for order in orders
    ]


@router.get("/pending-receipts", response_model=list[PurchaseReceiveCandidate])
def get_pending_receipts(db: Session = Depends(get_db)):
    return list_pending_purchase_receipts(db)


@router.post("/receive", response_model=InventoryTransactionRead)
def receive_purchase(payload: PurchaseReceiveCreate, db: Session = Depends(get_db)):
    try:
        transaction = receive_purchase_item(db, **payload.model_dump())
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


@router.post("/pending-receipts/bulk-delete", response_model=PurchasePendingReceiptDeleteResponse)
def delete_pending_receipts(payload: PurchasePendingReceiptDeleteRequest, db: Session = Depends(get_db)):
    try:
        deleted_item_ids = delete_pending_purchase_items(db, payload.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PurchasePendingReceiptDeleteResponse(
        deleted_count=len(deleted_item_ids),
        deleted_item_ids=deleted_item_ids,
    )
