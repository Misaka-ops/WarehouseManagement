import axios from 'axios'

import type {
  AuthLoginPayload,
  AuthLoginResponse,
  AuthSessionResponse,
  DashboardResponse,
  FeishuPurchasePreviewResponse,
  FeishuPurchaseSyncRequest,
  FeishuPurchaseImportResponse,
  FinishedDashboardResponse,
  FinishedInventoryManualCreatePayload,
  FinishedInventoryManualCreateResponse,
  FinishedInventoryTransaction,
  InventoryBulkDeleteResponse,
  InventoryImportResponse,
  InventoryManualUpsertPayload,
  InventoryManualUpsertResponse,
  InventoryTransaction,
  InventoryTransactionPayload,
  PurchaseImportItem,
  PurchaseImportResponse,
  PurchaseImportState,
  PurchasePendingReceipt,
  PurchasePendingReceiptDeleteResponse,
  PurchaseReceivePayload,
} from '../types/inventory'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '/api'

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
})

let accessToken = ''
let unauthorizedHandler: (() => void) | null = null

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      unauthorizedHandler?.()
    }
    return Promise.reject(error)
  },
)

export function setApiAccessToken(token: string | null) {
  accessToken = token?.trim() ?? ''
}

export function registerUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export async function postLogin(payload: AuthLoginPayload) {
  const { data } = await api.post<AuthLoginResponse>('/auth/login', payload)
  return data
}

export async function fetchAuthSession() {
  const { data } = await api.get<AuthSessionResponse>('/auth/session')
  return data
}

export async function fetchDashboard() {
  const { data } = await api.get<DashboardResponse>('/inventory/dashboard')
  return data
}

export async function fetchFinishedDashboard() {
  const { data } = await api.get<FinishedDashboardResponse>('/inventory/finished-dashboard')
  return data
}

export async function postReceipt(payload: InventoryTransactionPayload) {
  const { data } = await api.post('/inventory/receipt', payload)
  return data
}

export async function postIssue(payload: InventoryTransactionPayload) {
  const { data } = await api.post('/inventory/issue', payload)
  return data
}

export async function upsertInventoryItem(payload: InventoryManualUpsertPayload) {
  const { data } = await api.post<InventoryManualUpsertResponse>('/inventory/manual-upsert', payload)
  return data
}

export async function createFinishedInventoryItem(payload: FinishedInventoryManualCreatePayload) {
  const { data } = await api.post<FinishedInventoryManualCreateResponse>('/inventory/finished-manual-create', payload)
  return data
}

export async function fetchItemTransactions(itemId: number) {
  const { data } = await api.get<InventoryTransaction[]>(`/inventory/${itemId}/transactions`)
  return data
}

export async function fetchFinishedItemTransactions(rowId: number) {
  const { data } = await api.get<FinishedInventoryTransaction[]>(`/inventory/finished-items/${rowId}/transactions`)
  return data
}

export async function deleteInventoryItems(itemIds: number[]) {
  const { data } = await api.post<InventoryBulkDeleteResponse>('/inventory/bulk-delete', { item_ids: itemIds })
  return data
}

export async function importInventoryWorkbook(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<InventoryImportResponse>('/inventory/import-workbook', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function exportInventoryWorkbook() {
  const response = await api.get('/inventory/export-workbook', {
    responseType: 'blob',
  })

  const disposition = response.headers['content-disposition'] as string | undefined
  const matchedFilename = disposition?.match(/filename="(.+)"/)
  return {
    blob: response.data as Blob,
    filename: matchedFilename?.[1] ?? 'warehouse-export.xlsx',
  }
}

export async function fetchPendingReceipts() {
  const { data } = await api.get<PurchasePendingReceipt[]>('/purchases/pending-receipts')
  return data
}

export async function fetchPurchaseImportStates() {
  const { data } = await api.get<PurchaseImportState[]>('/purchases/import-states')
  return data
}

export async function updatePurchaseImportStates(states: Array<{ sheet_name: string; last_imported_row: number }>) {
  const { data } = await api.patch<PurchaseImportState[]>('/purchases/import-states', { states })
  return data
}

export async function importPurchaseWorkbook(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<PurchaseImportResponse>('/purchases/import-workbook', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
  return data
}

export async function updateImportedPurchaseItems(items: Array<{
  purchase_item_id: number
  material_name: string
  specification: string | null
  requested_quantity: number | null
  unit: string | null
  expected_arrival: string | null
  inventory_item_id: number | null
}>) {
  const { data } = await api.patch<{ updated_item_count: number; items: PurchaseImportItem[] }>('/purchases/imported-items', { items })
  return data
}

export async function receivePurchaseItem(payload: PurchaseReceivePayload) {
  const { data } = await api.post<InventoryTransaction>('/purchases/receive', payload)
  return data
}

export async function deletePendingPurchaseItems(itemIds: number[]) {
  const { data } = await api.post<PurchasePendingReceiptDeleteResponse>('/purchases/pending-receipts/bulk-delete', {
    item_ids: itemIds,
  })
  return data
}

export async function importFeishuPurchase(payload: FeishuPurchaseSyncRequest) {
  const { data } = await api.post<FeishuPurchaseImportResponse>('/purchases/feishu/import', payload, {
    timeout: 120000,
  })
  return data
}

export async function previewFeishuPurchase(payload: FeishuPurchaseSyncRequest) {
  const { data } = await api.post<FeishuPurchasePreviewResponse>('/purchases/feishu/preview', payload, {
    timeout: 120000,
  })
  return data
}
