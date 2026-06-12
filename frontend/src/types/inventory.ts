export type InventoryViewKind = 'raw' | 'finished'

export interface InventorySummary {
  total_items: number
  total_stock_quantity: string
  low_stock_items: number
  pending_purchase_orders: number
}

export interface AuthUser {
  username: string
  role: string
}

export interface AuthLoginPayload {
  username: string
  password: string
}

export interface AuthSessionResponse {
  authenticated: boolean
  user: AuthUser | null
  expires_at: string | null
}

export interface AuthLoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: AuthUser
}

export interface FeishuSettings {
  feishu_app_id: string | null
  feishu_app_secret: string | null
  feishu_purchase_approval_code: string | null
}

export interface InventoryItem {
  id: number
  requester: string | null
  purchase_category: string | null
  project_name: string | null
  item_code: string | null
  material_name: string
  specification: string | null
  unit: string | null
  supplier_name: string | null
  location_name: string | null
  quantity_on_hand: string
  total_amount: string | null
  notes: string | null
  last_receipt_at: string | null
  last_issue_at: string | null
}

export interface DashboardResponse {
  summary: InventorySummary
  items: InventoryItem[]
}

export interface FinishedInventorySummary {
  total_items: number
  total_stock_quantity: string
  low_stock_items: number
}

export interface FinishedInventoryItem {
  row_id: number
  material_name: string
  specification: string | null
  work_order_no: string | null
  quantity_on_hand: string
  unit: string | null
  location_name: string | null
  project_code: string | null
  producer_name: string | null
  customer_name: string | null
  notes: string | null
  last_receipt_at: string | null
  last_issue_at: string | null
}

export interface FinishedDashboardResponse {
  summary: FinishedInventorySummary
  items: FinishedInventoryItem[]
}

export interface FinishedInventoryTransaction {
  id: string
  row_id: number
  transaction_type: 'receipt' | 'issue'
  quantity: string
  occurred_on: string | null
  operator_name: string | null
  reference_code: string | null
  notes: string | null
}

export interface FinishedInventoryManualCreatePayload {
  material_name: string
  specification?: string | null
  unit?: string | null
  location_name: string
  quantity: number
  occurred_on: string
  work_order_no?: string | null
  project_code?: string | null
  producer_name?: string | null
  customer_name?: string | null
  notes?: string | null
}

export interface FinishedInventoryManualCreateResponse {
  item: FinishedInventoryItem
  transaction: FinishedInventoryTransaction
}

export interface FinishedInventoryBulkDeleteResponse {
  deleted_count: number
  deleted_row_ids: number[]
}

export interface InventoryImportResponse {
  workbook_name: string
  imported_item_count: number
  imported_transaction_count: number
  relinked_purchase_item_count: number
  replaced_item_count: number
}

export interface InventoryBulkDeleteResponse {
  deleted_count: number
  deleted_item_ids: number[]
}

export interface InventoryTransactionPayload {
  item_id: number
  quantity: number
  occurred_on: string
  total_amount?: number | null
  operator_name?: string
  reference_code?: string
  notes?: string
}

export interface InventoryTransaction {
  id: number
  item_id: number
  transaction_type: 'receipt' | 'issue'
  quantity: string
  occurred_on: string
  operator_name: string | null
  reference_code: string | null
  notes: string | null
}

export interface InventoryManualUpsertPayload {
  requester?: string | null
  purchase_category?: string | null
  project_name?: string | null
  item_code?: string | null
  material_name: string
  specification?: string | null
  unit?: string | null
  supplier_name?: string | null
  location_name?: string | null
  quantity: number
  total_amount?: number | null
  occurred_on: string
  operator_name?: string | null
  reference_code?: string | null
  item_notes?: string | null
  transaction_notes?: string | null
  notes?: string | null
}

export interface InventoryManualUpsertResponse {
  created_item: boolean
  item: InventoryItem
  transaction: InventoryTransaction
}

export interface PurchasePendingReceipt {
  purchase_item_id: number
  purchase_order_id: number
  sheet_name: string
  supplier_name: string | null
  requester: string | null
  item_code: string | null
  material_name: string
  specification: string | null
  requested_quantity: string | null
  received_quantity: string
  pending_quantity: string
  unit: string | null
  total_amount: string | null
  expected_arrival: string | null
  inventory_item_id: number | null
  location_name: string | null
}

export interface PurchaseImportState {
  sheet_name: string
  header_row: number
  last_imported_row: number
  last_workbook_name: string | null
  updated_at: string | null
}

export interface PurchaseImportItem {
  purchase_item_id: number
  purchase_order_id: number
  sheet_name: string
  source_row_number: number
  requester: string | null
  purchase_category: string | null
  project_name: string | null
  supplier_name: string | null
  contract_no: string | null
  material_name: string
  specification: string | null
  requested_quantity: string | null
  unit: string | null
  expected_arrival: string | null
  inventory_item_id: number | null
}

export interface PurchaseImportResponse {
  workbook_name: string
  imported_order_count: number
  imported_item_count: number
  unmatched_item_count: number
  updated_states: PurchaseImportState[]
  imported_items: PurchaseImportItem[]
  warnings: string[]
}

export interface FeishuPurchaseSyncRequest {
  approval_code?: string | null
  instance_codes?: string[]
  page_size?: number
  max_pages?: number
  time_range_days?: number | null
  filter_imported?: boolean
  filter_historical?: boolean
  force_reimport?: boolean
  locale?: string
}

export interface FeishuApprovalSyncState {
  approval_code: string
  last_synced_at: string | null
  last_synced_instance_code: string | null
  last_sync_status: string | null
  last_sync_message: string | null
  updated_at: string | null
}

export interface FeishuApprovalInstanceRecord {
  instance_code: string
  approval_code: string
  status: string | null
  title: string | null
  creator_name: string | null
  started_at: string | null
  finished_at: string | null
  raw_payload: string
  updated_at: string | null
}

export interface FeishuPurchaseSyncResponse {
  approval_code: string
  fetched_instance_count: number
  created_instance_count: number
  updated_instance_count: number
  skipped_instance_count: number
  filtered_imported_instance_count: number
  filtered_historical_instance_count: number
  sync_state: FeishuApprovalSyncState
  instances: FeishuApprovalInstanceRecord[]
  warnings: string[]
}

export interface FeishuPurchaseImportResponse extends FeishuPurchaseSyncResponse {
  reimported_order_count: number
  reimported_item_count: number
  imported_order_count: number
  imported_item_count: number
  skipped_import_count: number
}

export interface FeishuPurchasePreviewItem {
  line_no: number
  material_name: string
  specification: string | null
  requested_quantity: string | null
  unit: string | null
  total_amount: string | null
  link: string | null
  inventory_item_id: number | null
}

export interface FeishuPurchasePreviewOrder {
  instance_code: string
  approval_code: string
  status: string | null
  title: string | null
  requester: string | null
  creator_name: string | null
  purchase_category: string | null
  project_name: string | null
  requested_at: string | null
  ordered_at: string | null
  serial_number: string | null
  already_imported: boolean
  can_import: boolean
  skip_reason: string | null
  items: FeishuPurchasePreviewItem[]
}

export interface FeishuPurchasePreviewResponse {
  approval_code: string
  fetched_instance_count: number
  created_instance_count: number
  updated_instance_count: number
  skipped_instance_count: number
  filtered_imported_instance_count: number
  filtered_historical_instance_count: number
  importable_instance_count: number
  importable_item_count: number
  sync_state: FeishuApprovalSyncState
  orders: FeishuPurchasePreviewOrder[]
  warnings: string[]
}

export interface PurchaseReceivePayload {
  purchase_item_id: number
  quantity: number
  occurred_on: string
  total_amount?: number | null
  item_code?: string | null
  supplier_name?: string
  location_name?: string
  operator_name?: string
  reference_code?: string
  notes?: string
}

export interface PurchasePendingReceiptDeleteResponse {
  deleted_count: number
  deleted_item_ids: number[]
}
