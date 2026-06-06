from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.orm import Session, joinedload

from ..models import InventoryItem, InventoryTransaction, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus, TransactionType
from ..schemas import InventoryDashboardResponse, InventoryItemRead, InventorySummary, PurchaseReceiveCandidate
from .bootstrap import get_or_create_location, get_or_create_supplier, normalize_text


def _quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _resolve_inventory_item_total_amount(session: Session, item_id: int) -> Decimal | None:
    item = session.get(InventoryItem, item_id)
    if not item:
        return None
    if item.total_amount is not None:
        return Decimal(item.total_amount)

    purchase_total = session.scalar(
        select(
            func.sum(
                func.coalesce(
                    (PurchaseOrderItem.total_amount * PurchaseOrderItem.received_quantity)
                    / func.nullif(PurchaseOrderItem.requested_quantity, 0),
                    0,
                )
            )
        )
        .where(
            PurchaseOrderItem.inventory_item_id == item_id,
            PurchaseOrderItem.total_amount.is_not(None),
            PurchaseOrderItem.requested_quantity.is_not(None),
            PurchaseOrderItem.requested_quantity > 0,
            PurchaseOrderItem.received_quantity > 0,
        )
    )
    if purchase_total is None:
        return None

    return _quantize_amount(Decimal(purchase_total))


def _resolve_inventory_item_totals(session: Session, item_ids: list[int]) -> dict[int, Decimal]:
    if not item_ids:
        return {}

    rows = session.execute(
        select(
            PurchaseOrderItem.inventory_item_id,
            func.sum(
                func.coalesce(
                    (PurchaseOrderItem.total_amount * PurchaseOrderItem.received_quantity)
                    / func.nullif(PurchaseOrderItem.requested_quantity, 0),
                    0,
                )
            ),
        )
        .where(
            PurchaseOrderItem.inventory_item_id.in_(item_ids),
            PurchaseOrderItem.total_amount.is_not(None),
            PurchaseOrderItem.requested_quantity.is_not(None),
            PurchaseOrderItem.requested_quantity > 0,
            PurchaseOrderItem.received_quantity > 0,
        )
        .group_by(PurchaseOrderItem.inventory_item_id)
    ).all()
    return {
        int(inventory_item_id): _quantize_amount(Decimal(total_amount))
        for inventory_item_id, total_amount in rows
        if inventory_item_id is not None and total_amount is not None
    }


def _infer_purchase_item_amount(purchase_item: PurchaseOrderItem, quantity: Decimal) -> Decimal | None:
    if (
        purchase_item.total_amount is None
        or purchase_item.requested_quantity is None
        or Decimal(purchase_item.requested_quantity) <= 0
    ):
        return None

    inferred_amount = (Decimal(purchase_item.total_amount) * Decimal(quantity)) / Decimal(purchase_item.requested_quantity)
    return _quantize_amount(inferred_amount)


def build_dashboard(session: Session, *, include_sensitive: bool = True) -> InventoryDashboardResponse:
    items = session.scalars(
        select(InventoryItem)
        .options(joinedload(InventoryItem.supplier), joinedload(InventoryItem.location))
        .order_by(InventoryItem.quantity_on_hand.asc(), InventoryItem.material_name.asc())
    ).all()

    total_stock = session.scalar(select(func.coalesce(func.sum(InventoryItem.quantity_on_hand), 0))) or Decimal("0")
    pending_orders = session.scalar(
        select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status != PurchaseOrderStatus.completed)
    ) or 0
    fallback_totals = _resolve_inventory_item_totals(session, [item.id for item in items])

    item_reads = [
        InventoryItemRead(
            id=item.id,
            requester=item.requester if include_sensitive else None,
            purchase_category=item.purchase_category if include_sensitive else None,
            project_name=item.project_name if include_sensitive else None,
            item_code=item.item_code,
            material_name=item.material_name,
            specification=item.specification,
            unit=item.unit,
            supplier_name=item.supplier.name if include_sensitive and item.supplier else None,
            location_name=item.location.name if include_sensitive and item.location else None,
            quantity_on_hand=item.quantity_on_hand,
            total_amount=(Decimal(item.total_amount) if item.total_amount is not None else fallback_totals.get(item.id))
            if include_sensitive
            else None,
            notes=item.notes if include_sensitive else None,
            last_receipt_at=item.last_receipt_at if include_sensitive else None,
            last_issue_at=item.last_issue_at if include_sensitive else None,
        )
        for item in items
    ]

    return InventoryDashboardResponse(
        summary=InventorySummary(
            total_items=len(items),
            total_stock_quantity=Decimal(total_stock),
            low_stock_items=sum(1 for item in items if item.quantity_on_hand <= 5),
            pending_purchase_orders=int(pending_orders) if include_sensitive else 0,
        ),
        items=item_reads,
    )


def _find_inventory_item(
    session: Session,
    *,
    material_name: str,
    specification: str | None,
    unit: str | None,
    supplier_id: int | None,
    location_id: int | None,
) -> InventoryItem | None:
    conditions = [
        InventoryItem.material_name == material_name,
        InventoryItem.specification == specification,
        InventoryItem.unit == unit,
    ]
    if supplier_id is None:
        conditions.append(InventoryItem.supplier_id.is_(None))
    else:
        conditions.append(InventoryItem.supplier_id == supplier_id)

    if location_id is None:
        conditions.append(InventoryItem.location_id.is_(None))
    else:
        conditions.append(InventoryItem.location_id == location_id)

    return session.scalar(select(InventoryItem).where(and_(*conditions)).order_by(InventoryItem.id.asc()))


def create_transaction(
    session: Session,
    *,
    item_id: int,
    quantity: Decimal,
    occurred_on: date,
    total_amount: Decimal | None,
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

    current_quantity = Decimal(item.quantity_on_hand)
    if transaction_type == TransactionType.receipt:
        item.quantity_on_hand = current_quantity + quantity
        if total_amount is not None:
            base_amount = _resolve_inventory_item_total_amount(session, item.id) or Decimal("0")
            item.total_amount = _quantize_amount(base_amount + Decimal(total_amount))
    else:
        item.quantity_on_hand = current_quantity - quantity
        current_total_amount = _resolve_inventory_item_total_amount(session, item.id)
        if current_total_amount is not None and current_quantity > 0:
            amount_delta = _quantize_amount((current_total_amount * Decimal(quantity)) / current_quantity)
            next_total_amount = current_total_amount - amount_delta
            item.total_amount = _quantize_amount(max(next_total_amount, Decimal("0")))

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


def upsert_inventory_item(
    session: Session,
    *,
    requester: str | None,
    purchase_category: str | None,
    project_name: str | None,
    item_code: str | None,
    material_name: str,
    specification: str | None,
    unit: str | None,
    supplier_name: str | None,
    location_name: str | None,
    quantity: Decimal,
    total_amount: Decimal | None,
    occurred_on: date,
    operator_name: str | None,
    reference_code: str | None,
    item_notes: str | None = None,
    transaction_notes: str | None = None,
    notes: str | None = None,
) -> tuple[InventoryItem, InventoryTransaction, bool]:
    normalized_material_name = normalize_text(material_name)
    if not normalized_material_name:
        raise ValueError("Material name is required.")

    normalized_specification = normalize_text(specification)
    normalized_unit = normalize_text(unit)
    normalized_requester = normalize_text(requester)
    normalized_purchase_category = normalize_text(purchase_category)
    normalized_project_name = normalize_text(project_name)
    normalized_item_code = normalize_text(item_code)
    normalized_supplier_name = normalize_text(supplier_name)
    normalized_location_name = normalize_text(location_name)
    normalized_total_amount = Decimal(total_amount) if total_amount is not None else None
    normalized_item_notes = normalize_text(item_notes if item_notes is not None else notes)
    normalized_transaction_notes = normalize_text(transaction_notes if transaction_notes is not None else notes)
    normalized_operator_name = normalize_text(operator_name)
    normalized_reference_code = normalize_text(reference_code)

    supplier = get_or_create_supplier(session, normalized_supplier_name)
    location = get_or_create_location(session, normalized_location_name)

    item = _find_inventory_item(
        session,
        material_name=normalized_material_name,
        specification=normalized_specification,
        unit=normalized_unit,
        supplier_id=supplier.id if supplier else None,
        location_id=location.id if location else None,
    )

    created_item = item is None
    if created_item:
        item = InventoryItem(
            requester=normalized_requester,
            purchase_category=normalized_purchase_category,
            project_name=normalized_project_name,
            item_code=normalized_item_code,
            material_name=normalized_material_name,
            specification=normalized_specification,
            unit=normalized_unit,
            supplier=supplier,
            location=location,
            quantity_on_hand=Decimal("0"),
            total_amount=_quantize_amount(normalized_total_amount) if normalized_total_amount is not None else None,
            notes=normalized_item_notes,
        )
        session.add(item)
        session.flush()
    else:
        item.requester = normalized_requester
        item.purchase_category = normalized_purchase_category
        item.project_name = normalized_project_name
        if normalized_item_code is not None:
            item.item_code = normalized_item_code
        item.material_name = normalized_material_name
        item.specification = normalized_specification
        item.unit = normalized_unit
        item.supplier = supplier
        item.location = location
        if normalized_total_amount is not None:
            base_amount = _resolve_inventory_item_total_amount(session, item.id) or Decimal("0")
            item.total_amount = _quantize_amount(base_amount + normalized_total_amount)
        item.notes = normalized_item_notes

    item.quantity_on_hand = Decimal(item.quantity_on_hand) + quantity
    item.last_receipt_at = occurred_on

    transaction = InventoryTransaction(
        item_id=item.id,
        transaction_type=TransactionType.receipt,
        quantity=quantity,
        occurred_on=occurred_on,
        operator_name=normalized_operator_name,
        reference_code=normalized_reference_code,
        notes=normalized_transaction_notes or "手动录入库存",
    )
    session.add(transaction)
    session.commit()
    session.refresh(item)
    session.refresh(transaction)
    return item, transaction, created_item


def list_item_transactions(session: Session, item_id: int, limit: int = 12) -> list[InventoryTransaction]:
    return session.scalars(
        select(InventoryTransaction)
        .where(InventoryTransaction.item_id == item_id)
        .order_by(InventoryTransaction.occurred_on.desc(), InventoryTransaction.id.desc())
        .limit(limit)
    ).all()


def _refresh_purchase_order_status(order: PurchaseOrder) -> None:
    order_items = order.items
    if not order_items:
        order.status = PurchaseOrderStatus.pending
        return

    if all((line.requested_quantity or Decimal("0")) <= (line.received_quantity or Decimal("0")) for line in order_items):
        order.status = PurchaseOrderStatus.completed
    elif any((line.received_quantity or Decimal("0")) > 0 for line in order_items):
        order.status = PurchaseOrderStatus.partial
    else:
        order.status = PurchaseOrderStatus.pending


def _should_purge_feishu_purchase_order_after_inventory_reset(order: PurchaseOrder) -> bool:
    if order.feishu_meta is None:
        return False

    return all(
        (line.received_quantity or Decimal("0")) <= Decimal("0") and line.inventory_item_id is None
        for line in order.items
    )


def delete_inventory_items(session: Session, item_ids: list[int]) -> list[int]:
    normalized_ids = sorted(set(item_ids))
    if not normalized_ids:
        raise ValueError("No inventory items selected for deletion.")

    items = session.scalars(
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.purchase_items)
            .joinedload(PurchaseOrderItem.order)
            .joinedload(PurchaseOrder.items),
            joinedload(InventoryItem.purchase_items).joinedload(PurchaseOrderItem.order).joinedload(PurchaseOrder.feishu_meta),
        )
        .where(InventoryItem.id.in_(normalized_ids))
    ).unique().all()
    existing_ids = sorted({item.id for item in items})
    if not items:
        raise ValueError("Selected inventory items were not found.")

    touched_order_ids: set[int] = set()
    for item in items:
        for purchase_item in item.purchase_items:
            purchase_item.inventory_item_id = None
            purchase_item.received_quantity = Decimal("0")
            touched_order_ids.add(purchase_item.order_id)

    if touched_order_ids:
        touched_orders = session.scalars(
            select(PurchaseOrder)
            .options(joinedload(PurchaseOrder.items), joinedload(PurchaseOrder.feishu_meta))
            .where(PurchaseOrder.id.in_(touched_order_ids))
        ).unique().all()
        for order in touched_orders:
            if _should_purge_feishu_purchase_order_after_inventory_reset(order):
                session.delete(order)
                continue
            _refresh_purchase_order_status(order)

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
        .options(joinedload(PurchaseOrderItem.order), joinedload(PurchaseOrderItem.inventory_item).joinedload(InventoryItem.location))
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
                item_code=item.inventory_item.item_code if item.inventory_item else None,
                material_name=item.material_name,
                specification=item.specification,
                requested_quantity=item.requested_quantity,
                received_quantity=item.received_quantity,
                pending_quantity=pending,
                unit=item.unit,
                total_amount=_infer_purchase_item_amount(item, pending),
                expected_arrival=item.expected_arrival,
                inventory_item_id=item.inventory_item_id,
                location_name=item.inventory_item.location.name if item.inventory_item and item.inventory_item.location else None,
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
    total_amount: Decimal | None,
    item_code: str | None,
    supplier_name: str | None,
    location_name: str | None,
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

    normalized_supplier_name = normalize_text(supplier_name)
    normalized_location_name = normalize_text(location_name)
    normalized_item_code = normalize_text(item_code)
    supplier = get_or_create_supplier(session, normalized_supplier_name)
    location = get_or_create_location(session, normalized_location_name)
    inventory_item = purchase_item.inventory_item
    receipt_amount = Decimal(total_amount) if total_amount is not None else _infer_purchase_item_amount(purchase_item, quantity)
    if normalized_supplier_name is not None:
        purchase_item.order.supplier_name = normalized_supplier_name
    if not inventory_item:
        inventory_item = InventoryItem(
            requester=purchase_item.order.requester,
            purchase_category=purchase_item.order.purchase_category,
            project_name=purchase_item.order.project_name,
            item_code=normalized_item_code,
            material_name=purchase_item.material_name,
            specification=purchase_item.specification,
            unit=purchase_item.unit,
            supplier=supplier,
            location=location,
            quantity_on_hand=Decimal("0"),
            total_amount=_quantize_amount(receipt_amount) if receipt_amount is not None else None,
            notes=None,
        )
        session.add(inventory_item)
        session.flush()
        purchase_item.inventory_item_id = inventory_item.id
    else:
        if normalized_item_code is not None:
            inventory_item.item_code = normalized_item_code
        if normalized_supplier_name is not None:
            inventory_item.supplier = supplier
        if location is not None:
            inventory_item.location = location
        if receipt_amount is not None:
            base_amount = _resolve_inventory_item_total_amount(session, inventory_item.id) or Decimal("0")
            inventory_item.total_amount = _quantize_amount(base_amount + receipt_amount)

    inventory_item.quantity_on_hand = Decimal(inventory_item.quantity_on_hand) + quantity
    inventory_item.last_receipt_at = occurred_on

    purchase_item.received_quantity = Decimal(received_quantity) + quantity

    order = purchase_item.order
    _refresh_purchase_order_status(order)

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
