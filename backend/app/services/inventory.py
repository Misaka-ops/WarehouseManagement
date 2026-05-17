from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, joinedload

from ..models import InventoryItem, InventoryTransaction, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus, TransactionType
from ..schemas import InventoryDashboardResponse, InventoryItemRead, InventorySummary, PurchaseReceiveCandidate


def build_dashboard(session: Session) -> InventoryDashboardResponse:
    items = session.scalars(
        select(InventoryItem)
        .options(joinedload(InventoryItem.supplier), joinedload(InventoryItem.location))
        .order_by(InventoryItem.quantity_on_hand.asc(), InventoryItem.material_name.asc())
    ).all()

    total_stock = session.scalar(select(func.coalesce(func.sum(InventoryItem.quantity_on_hand), 0))) or Decimal("0")
    pending_orders = session.scalar(
        select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status != PurchaseOrderStatus.completed)
    ) or 0

    item_reads = [
        InventoryItemRead(
            id=item.id,
            requester=item.requester,
            purchase_category=item.purchase_category,
            project_name=item.project_name,
            material_name=item.material_name,
            specification=item.specification,
            unit=item.unit,
            supplier_name=item.supplier.name if item.supplier else None,
            location_name=item.location.name if item.location else None,
            quantity_on_hand=item.quantity_on_hand,
            notes=item.notes,
            last_receipt_at=item.last_receipt_at,
            last_issue_at=item.last_issue_at,
        )
        for item in items
    ]

    return InventoryDashboardResponse(
        summary=InventorySummary(
            total_items=len(items),
            total_stock_quantity=Decimal(total_stock),
            low_stock_items=sum(1 for item in items if item.quantity_on_hand <= 5),
            pending_purchase_orders=int(pending_orders),
        ),
        items=item_reads,
    )


def create_transaction(
    session: Session,
    *,
    item_id: int,
    quantity: Decimal,
    occurred_on: date,
    operator_name: str | None,
    reference_code: str | None,
    notes: str | None,
    transaction_type: TransactionType,
) -> InventoryTransaction:
    item = session.get(InventoryItem, item_id)
    if not item:
        raise ValueError("Inventory item not found.")

    if transaction_type == TransactionType.issue and item.quantity_on_hand < quantity:
        raise ValueError("Insufficient stock for issue transaction.")

    item.quantity_on_hand = Decimal(item.quantity_on_hand) + quantity if transaction_type == TransactionType.receipt else Decimal(item.quantity_on_hand) - quantity

    if transaction_type == TransactionType.receipt:
        item.last_receipt_at = occurred_on
    else:
        item.last_issue_at = occurred_on

    transaction = InventoryTransaction(
        item_id=item.id,
        transaction_type=transaction_type,
        quantity=quantity,
        occurred_on=occurred_on,
        operator_name=operator_name,
        reference_code=reference_code,
        notes=notes,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def list_item_transactions(session: Session, item_id: int, limit: int = 12) -> list[InventoryTransaction]:
    return session.scalars(
        select(InventoryTransaction)
        .where(InventoryTransaction.item_id == item_id)
        .order_by(InventoryTransaction.occurred_on.desc(), InventoryTransaction.id.desc())
        .limit(limit)
    ).all()


def delete_inventory_items(session: Session, item_ids: list[int]) -> list[int]:
    normalized_ids = sorted(set(item_ids))
    if not normalized_ids:
        raise ValueError("No inventory items selected for deletion.")

    existing_ids = session.scalars(
        select(InventoryItem.id).where(InventoryItem.id.in_(normalized_ids))
    ).all()
    existing_ids = sorted(set(existing_ids))
    if not existing_ids:
        raise ValueError("Selected inventory items were not found.")

    session.execute(
        update(PurchaseOrderItem)
        .where(PurchaseOrderItem.inventory_item_id.in_(existing_ids))
        .values(inventory_item_id=None)
    )
    session.execute(delete(InventoryTransaction).where(InventoryTransaction.item_id.in_(existing_ids)))
    session.execute(delete(InventoryItem).where(InventoryItem.id.in_(existing_ids)))
    session.commit()
    return existing_ids


def list_pending_purchase_receipts(session: Session, limit: int = 40) -> list[PurchaseReceiveCandidate]:
    rows = session.scalars(
        select(PurchaseOrderItem)
        .options(joinedload(PurchaseOrderItem.order))
        .order_by(PurchaseOrderItem.id.desc())
    ).all()

    candidates: list[PurchaseReceiveCandidate] = []
    for item in rows:
        requested = item.requested_quantity or Decimal("0")
        pending = requested - (item.received_quantity or Decimal("0"))
        if pending <= 0:
            continue

        candidates.append(
            PurchaseReceiveCandidate(
                purchase_item_id=item.id,
                purchase_order_id=item.order_id,
                sheet_name=item.order.sheet_name,
                supplier_name=item.order.supplier_name,
                requester=item.order.requester,
                material_name=item.material_name,
                specification=item.specification,
                requested_quantity=item.requested_quantity,
                received_quantity=item.received_quantity,
                pending_quantity=pending,
                unit=item.unit,
                expected_arrival=item.expected_arrival,
                inventory_item_id=item.inventory_item_id,
            )
        )

        if len(candidates) >= limit:
            break

    return candidates


def receive_purchase_item(
    session: Session,
    *,
    purchase_item_id: int,
    quantity: Decimal,
    occurred_on: date,
    operator_name: str | None,
    reference_code: str | None,
    notes: str | None,
) -> InventoryTransaction:
    purchase_item = session.get(PurchaseOrderItem, purchase_item_id)
    if not purchase_item:
        raise ValueError("Purchase order item not found.")

    requested_quantity = purchase_item.requested_quantity or Decimal("0")
    received_quantity = purchase_item.received_quantity or Decimal("0")
    pending_quantity = requested_quantity - received_quantity
    if pending_quantity <= 0:
        raise ValueError("This purchase item has already been fully received.")
    if quantity > pending_quantity:
        raise ValueError("Receipt quantity exceeds the pending quantity.")

    inventory_item = purchase_item.inventory_item
    if not inventory_item:
        inventory_item = InventoryItem(
            requester=purchase_item.order.requester,
            purchase_category=purchase_item.order.purchase_category,
            project_name=purchase_item.order.project_name,
            material_name=purchase_item.material_name,
            specification=purchase_item.specification,
            unit=purchase_item.unit,
            quantity_on_hand=Decimal("0"),
            notes=None,
        )
        session.add(inventory_item)
        session.flush()
        purchase_item.inventory_item_id = inventory_item.id

    inventory_item.quantity_on_hand = Decimal(inventory_item.quantity_on_hand) + quantity
    inventory_item.last_receipt_at = occurred_on

    purchase_item.received_quantity = Decimal(received_quantity) + quantity

    order = purchase_item.order
    order_items = order.items
    if all((line.requested_quantity or Decimal("0")) <= (line.received_quantity or Decimal("0")) for line in order_items):
      order.status = PurchaseOrderStatus.completed
    elif any((line.received_quantity or Decimal("0")) > 0 for line in order_items):
      order.status = PurchaseOrderStatus.partial

    transaction = InventoryTransaction(
        item_id=inventory_item.id,
        transaction_type=TransactionType.receipt,
        quantity=quantity,
        occurred_on=occurred_on,
        operator_name=operator_name,
        reference_code=reference_code,
        notes=notes or f"采购单明细收货 #{purchase_item.id}",
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction
