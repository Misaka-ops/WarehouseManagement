from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventorySummary(BaseModel):
    total_items: int
    total_stock_quantity: Decimal
    low_stock_items: int
    pending_purchase_orders: int


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requester: str | None
    purchase_category: str | None
    project_name: str | None
    material_name: str
    specification: str | None
    unit: str | None
    supplier_name: str | None = None
    location_name: str | None = None
    quantity_on_hand: Decimal
    total_amount: Decimal | None = None
    notes: str | None
    last_receipt_at: date | None
    last_issue_at: date | None


class InventoryDashboardResponse(BaseModel):
    summary: InventorySummary
    items: list[InventoryItemRead]


class InventoryImportResponse(BaseModel):
    workbook_name: str
    imported_item_count: int
    imported_transaction_count: int
    relinked_purchase_item_count: int
    replaced_item_count: int


class InventoryBulkDeleteRequest(BaseModel):
    item_ids: list[int] = Field(min_length=1)


class InventoryBulkDeleteResponse(BaseModel):
    deleted_count: int
    deleted_item_ids: list[int]


class InventoryTransactionCreate(BaseModel):
    item_id: int
    quantity: Decimal = Field(gt=0)
    occurred_on: date
    total_amount: Decimal | None = Field(default=None, ge=0)
    operator_name: str | None = None
    reference_code: str | None = None
    notes: str | None = None


class InventoryTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    transaction_type: str
    quantity: Decimal
    occurred_on: date
    operator_name: str | None
    reference_code: str | None
    notes: str | None


class InventoryManualUpsertRequest(BaseModel):
    requester: str | None = None
    purchase_category: str | None = None
    project_name: str | None = None
    material_name: str
    specification: str | None = None
    unit: str | None = None
    supplier_name: str | None = None
    location_name: str | None = None
    quantity: Decimal = Field(gt=0)
    total_amount: Decimal | None = Field(default=None, ge=0)
    occurred_on: date
    operator_name: str | None = None
    reference_code: str | None = None
    item_notes: str | None = None
    transaction_notes: str | None = None
    notes: str | None = None


class InventoryManualUpsertResponse(BaseModel):
    created_item: bool
    item: InventoryItemRead
    transaction: InventoryTransactionRead


class PurchaseReceiveCreate(BaseModel):
    purchase_item_id: int
    quantity: Decimal = Field(gt=0)
    occurred_on: date
    total_amount: Decimal | None = Field(default=None, ge=0)
    location_name: str | None = None
    operator_name: str | None = None
    reference_code: str | None = None
    notes: str | None = None


class PurchasePendingReceiptDeleteRequest(BaseModel):
    item_ids: list[int] = Field(min_length=1)


class PurchasePendingReceiptDeleteResponse(BaseModel):
    deleted_count: int
    deleted_item_ids: list[int]


class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_no: int
    material_name: str
    specification: str | None
    requested_quantity: Decimal | None
    received_quantity: Decimal
    unit: str | None
    unit_price: Decimal | None
    total_amount: Decimal | None
    expected_arrival: date | None
    pending_quantity: Decimal | None = None


class PurchaseImportStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sheet_name: str
    header_row: int
    last_imported_row: int
    last_workbook_name: str | None
    updated_at: datetime | None = None


class PurchaseImportStateUpdate(BaseModel):
    sheet_name: str
    last_imported_row: int = Field(ge=0)


class PurchaseImportStateUpdateRequest(BaseModel):
    states: list[PurchaseImportStateUpdate] = Field(min_length=1)


class FeishuPurchaseSyncRequest(BaseModel):
    approval_code: str | None = None
    instance_codes: list[str] = Field(default_factory=list)
    page_size: int = Field(default=20, ge=1, le=100)
    max_pages: int = Field(default=3, ge=1, le=20)
    time_range_days: int | None = Field(default=None, ge=1, le=365)
    filter_imported: bool = False
    filter_historical: bool = False
    force_reimport: bool = False
    locale: str = "zh-CN"


class FeishuPurchaseImportRequest(FeishuPurchaseSyncRequest):
    pass


class FeishuApprovalSyncStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_code: str
    last_synced_at: datetime | None
    last_synced_instance_code: str | None
    last_sync_status: str | None
    last_sync_message: str | None
    updated_at: datetime | None = None


class FeishuApprovalInstanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    instance_code: str
    approval_code: str
    status: str | None
    title: str | None
    creator_name: str | None
    started_at: datetime | None
    finished_at: datetime | None
    raw_payload: str
    updated_at: datetime | None = None


class FeishuApprovalDefinitionRead(BaseModel):
    approval_code: str
    approval_name: str | None
    status: str | None
    raw_payload: str


class FeishuInstancePullRequest(BaseModel):
    instance_code: str
    approval_code: str | None = None
    locale: str = "zh-CN"


class FeishuPurchaseSyncResponse(BaseModel):
    approval_code: str
    fetched_instance_count: int
    created_instance_count: int
    updated_instance_count: int
    skipped_instance_count: int
    filtered_imported_instance_count: int = 0
    filtered_historical_instance_count: int = 0
    sync_state: FeishuApprovalSyncStateRead
    instances: list[FeishuApprovalInstanceRecordRead]
    warnings: list[str] = Field(default_factory=list)


class FeishuPurchaseImportResponse(BaseModel):
    approval_code: str
    fetched_instance_count: int
    created_instance_count: int
    updated_instance_count: int
    reimported_order_count: int = 0
    reimported_item_count: int = 0
    imported_order_count: int
    imported_item_count: int
    skipped_instance_count: int
    skipped_import_count: int
    filtered_imported_instance_count: int = 0
    filtered_historical_instance_count: int = 0
    sync_state: FeishuApprovalSyncStateRead
    instances: list[FeishuApprovalInstanceRecordRead]
    warnings: list[str] = Field(default_factory=list)


class FeishuPurchasePreviewItemRead(BaseModel):
    line_no: int
    material_name: str
    specification: str | None
    requested_quantity: Decimal | None
    unit: str | None
    total_amount: Decimal | None
    link: str | None
    inventory_item_id: int | None


class FeishuPurchasePreviewOrderRead(BaseModel):
    instance_code: str
    approval_code: str
    status: str | None
    title: str | None
    requester: str | None
    creator_name: str | None
    purchase_category: str | None
    project_name: str | None
    requested_at: date | None
    ordered_at: date | None
    serial_number: str | None
    already_imported: bool = False
    can_import: bool = False
    skip_reason: str | None = None
    items: list[FeishuPurchasePreviewItemRead] = Field(default_factory=list)


class FeishuPurchasePreviewResponse(BaseModel):
    approval_code: str
    fetched_instance_count: int
    created_instance_count: int
    updated_instance_count: int
    skipped_instance_count: int
    filtered_imported_instance_count: int = 0
    filtered_historical_instance_count: int = 0
    importable_instance_count: int = 0
    importable_item_count: int = 0
    sync_state: FeishuApprovalSyncStateRead
    orders: list[FeishuPurchasePreviewOrderRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PurchaseImportItemRead(BaseModel):
    purchase_item_id: int
    purchase_order_id: int
    sheet_name: str
    source_row_number: int
    requester: str | None
    purchase_category: str | None
    project_name: str | None
    supplier_name: str | None
    contract_no: str | None
    material_name: str
    specification: str | None
    requested_quantity: Decimal | None
    unit: str | None
    expected_arrival: date | None
    inventory_item_id: int | None


class PurchaseImportResponse(BaseModel):
    workbook_name: str
    imported_order_count: int
    imported_item_count: int
    unmatched_item_count: int
    updated_states: list[PurchaseImportStateRead]
    imported_items: list[PurchaseImportItemRead]
    warnings: list[str] = Field(default_factory=list)


class PurchaseImportedItemUpdate(BaseModel):
    purchase_item_id: int
    material_name: str
    specification: str | None = None
    requested_quantity: Decimal | None = None
    unit: str | None = None
    expected_arrival: date | None = None
    inventory_item_id: int | None = None


class PurchaseImportedItemsAdjustRequest(BaseModel):
    items: list[PurchaseImportedItemUpdate] = Field(min_length=1)


class PurchaseImportedItemsAdjustResponse(BaseModel):
    updated_item_count: int
    items: list[PurchaseImportItemRead]


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sheet_name: str
    requester: str | None
    purchase_category: str | None
    project_name: str | None
    supplier_name: str | None
    status: str
    requested_at: date | None
    ordered_at: date | None
    contract_no: str | None
    notes: str | None
    items: list[PurchaseOrderItemRead]


class PurchaseReceiveCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purchase_item_id: int
    purchase_order_id: int
    sheet_name: str
    supplier_name: str | None
    requester: str | None
    material_name: str
    specification: str | None
    requested_quantity: Decimal | None
    received_quantity: Decimal
    pending_quantity: Decimal
    unit: str | None
    total_amount: Decimal | None = None
    expected_arrival: date | None
    inventory_item_id: int | None
    location_name: str | None = None
