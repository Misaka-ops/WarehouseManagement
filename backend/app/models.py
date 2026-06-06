from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TransactionType(str, Enum):
    receipt = "receipt"
    issue = "issue"


class PurchaseOrderStatus(str, Enum):
    pending = "pending"
    partial = "partial"
    completed = "completed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    items: Mapped[list[InventoryItem]] = relationship(back_populates="supplier")


class Location(TimestampMixin, Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    items: Mapped[list[InventoryItem]] = relationship(back_populates="location")


class InventoryItem(TimestampMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("material_name", "specification", "unit", "supplier_id", "location_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    requester: Mapped[str | None] = mapped_column(String(80))
    purchase_category: Mapped[str | None] = mapped_column(String(80))
    project_name: Mapped[str | None] = mapped_column(String(120))
    item_code: Mapped[str | None] = mapped_column(String(120))
    material_name: Mapped[str] = mapped_column(String(200), index=True)
    specification: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(40))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    last_receipt_at: Mapped[date | None] = mapped_column(Date)
    last_issue_at: Mapped[date | None] = mapped_column(Date)

    supplier: Mapped[Supplier | None] = relationship(back_populates="items")
    location: Mapped[Location | None] = relationship(back_populates="items")
    transactions: Mapped[list[InventoryTransaction]] = relationship(back_populates="item")
    purchase_items: Mapped[list[PurchaseOrderItem]] = relationship(back_populates="inventory_item")


class PurchaseOrder(TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    sheet_name: Mapped[str] = mapped_column(String(80))
    requester: Mapped[str | None] = mapped_column(String(80))
    purchase_category: Mapped[str | None] = mapped_column(String(80))
    project_name: Mapped[str | None] = mapped_column(String(120))
    supplier_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[PurchaseOrderStatus] = mapped_column(SqlEnum(PurchaseOrderStatus), default=PurchaseOrderStatus.pending)
    requested_at: Mapped[date | None] = mapped_column(Date)
    ordered_at: Mapped[date | None] = mapped_column(Date)
    contract_no: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[PurchaseOrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    feishu_meta: Mapped[FeishuPurchaseOrderMeta | None] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(TimestampMixin, Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    inventory_item_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_items.id"))
    line_no: Mapped[int] = mapped_column()
    material_name: Mapped[str] = mapped_column(String(200))
    specification: Mapped[str | None] = mapped_column(String(255))
    requested_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    unit: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_arrival: Mapped[date | None] = mapped_column(Date)

    order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    inventory_item: Mapped[InventoryItem | None] = relationship(back_populates="purchase_items")
    import_meta: Mapped[PurchaseImportItemMeta | None] = relationship(back_populates="purchase_item", cascade="all, delete-orphan")
    feishu_meta: Mapped[FeishuPurchaseItemMeta | None] = relationship(back_populates="purchase_item", cascade="all, delete-orphan")


class PurchaseImportItemMeta(TimestampMixin, Base):
    __tablename__ = "purchase_import_item_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_item_id: Mapped[int] = mapped_column(ForeignKey("purchase_order_items.id"), unique=True, index=True)
    source_row_number: Mapped[int] = mapped_column()

    purchase_item: Mapped[PurchaseOrderItem] = relationship(back_populates="import_meta")


class PurchaseImportState(TimestampMixin, Base):
    __tablename__ = "purchase_import_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    sheet_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    header_row: Mapped[int] = mapped_column(default=2)
    last_imported_row: Mapped[int] = mapped_column(default=2)
    last_workbook_name: Mapped[str | None] = mapped_column(String(255))


class FeishuPurchaseOrderMeta(TimestampMixin, Base):
    __tablename__ = "feishu_purchase_order_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_instance_code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    approval_code: Mapped[str] = mapped_column(String(120), index=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), unique=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(120))
    approval_status: Mapped[str | None] = mapped_column(String(80))

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="feishu_meta")


class FeishuPurchaseItemMeta(TimestampMixin, Base):
    __tablename__ = "feishu_purchase_item_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_item_id: Mapped[int] = mapped_column(ForeignKey("purchase_order_items.id"), unique=True, index=True)
    approval_instance_code: Mapped[str] = mapped_column(String(120), index=True)
    source_line_no: Mapped[int] = mapped_column()

    purchase_item: Mapped[PurchaseOrderItem] = relationship(back_populates="feishu_meta")


class FeishuApprovalSyncState(TimestampMixin, Base):
    __tablename__ = "feishu_approval_sync_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_synced_instance_code: Mapped[str | None] = mapped_column(String(120))
    last_sync_status: Mapped[str | None] = mapped_column(String(80))
    last_sync_message: Mapped[str | None] = mapped_column(Text)


class FeishuApprovalInstanceRecord(TimestampMixin, Base):
    __tablename__ = "feishu_approval_instance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    approval_code: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(255))
    creator_name: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    raw_payload: Mapped[str] = mapped_column(Text)


class InventoryTransaction(TimestampMixin, Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    transaction_type: Mapped[TransactionType] = mapped_column(SqlEnum(TransactionType))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    occurred_on: Mapped[date] = mapped_column(Date)
    operator_name: Mapped[str | None] = mapped_column(String(80))
    reference_code: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    item: Mapped[InventoryItem] = relationship(back_populates="transactions")
