export interface InventorySummary {
  total_items: number
  total_stock_quantity: string
  low_stock_items: number
  pending_purchase_orders: number
}

export interface InventoryItem {
  id: number
  requester: string | null
  purchase_category: string | null
  project_name: string | null
  material_name: string
  specification: string | null
  unit: string | null
  supplier_name: string | null
  location_name: string | null
  quantity_on_hand: string
  notes: string | null
  last_receipt_at: string | null
  last_issue_at: string | null
}

export interface DashboardResponse {
  summary: InventorySummary
  items: InventoryItem[]
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

export interface PurchasePendingReceipt {
  purchase_item_id: number
  purchase_order_id: number
  sheet_name: string
  supplier_name: string | null
  requester: string | null
  material_name: string
  specification: string | null
  requested_quantity: string | null
  received_quantity: string
  pending_quantity: string
  unit: string | null
  expected_arrival: string | null
  inventory_item_id: number | null
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

export interface PurchaseReceivePayload {
  purchase_item_id: number
  quantity: number
  occurred_on: string
  operator_name?: string
  reference_code?: string
  notes?: string
}

export interface PurchasePendingReceiptDeleteResponse {
  deleted_count: number
  deleted_item_ids: number[]
}
