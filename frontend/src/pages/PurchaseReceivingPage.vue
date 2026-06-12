<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'
import { deletePendingPurchaseItems, receivePurchaseItem } from '../services/api'
import type { PurchasePendingReceipt, PurchaseReceivePayload } from '../types/inventory'

type ReceiveMode = 'single' | 'batch'

const route = useRoute()
const { dashboard, loadDashboard } = useInventoryWorkspace()
const {
  choosePendingReceipt,
  loadPendingReceipts,
  pendingReceipts,
  pendingReceiptsLoading,
  selectedPendingReceipt,
  selectedPendingReceiptId,
} = usePendingReceipts()

const receiving = ref(false)
const deleting = ref(false)
const receiveMode = ref<ReceiveMode>('single')
const selectedItemIds = ref<number[]>([])
const searchKeyword = ref('')
const locationMissingOnly = ref(false)
const receiptForm = ref<PurchaseReceivePayload>({
  purchase_item_id: 0,
  quantity: 1,
  occurred_on: new Date().toISOString().slice(0, 10),
  total_amount: null,
  item_code: '',
  supplier_name: '',
  location_name: '',
  operator_name: '',
  reference_code: 'RK-PO-',
  notes: '',
})
const sourceKey = computed(() => (typeof route.query.source === 'string' ? route.query.source : ''))
const scopedPurchaseItemIds = computed(() => {
  const rawValue = typeof route.query.purchaseItemIds === 'string' ? route.query.purchaseItemIds : ''
  if (!rawValue.trim()) {
    return []
  }

  return [...new Set(rawValue.split(',').map((value) => Number(value.trim())).filter((value) => Number.isFinite(value) && value > 0))]
})
const scopedPendingReceipts = computed(() => {
  if (!scopedPurchaseItemIds.value.length) {
    return pendingReceipts.value
  }

  const scopedIdSet = new Set(scopedPurchaseItemIds.value)
  return pendingReceipts.value.filter((item) => scopedIdSet.has(item.purchase_item_id))
})
const scopeMissingCount = computed(() => {
  if (!scopedPurchaseItemIds.value.length) {
    return 0
  }

  const currentIds = new Set(pendingReceipts.value.map((item) => item.purchase_item_id))
  return scopedPurchaseItemIds.value.filter((itemId) => !currentIds.has(itemId)).length
})
const scopeTitle = computed(() => {
  if (!scopedPurchaseItemIds.value.length) {
    return ''
  }

  if (sourceKey.value === 'purchase-import') {
    return `仅查看本次导入的 ${scopedPendingReceipts.value.length} 条待收货`
  }

  return `已按上下文锁定 ${scopedPendingReceipts.value.length} 条待收货`
})
const scopeDescription = computed(() => {
  if (!scopedPurchaseItemIds.value.length) {
    return ''
  }

  if (scopeMissingCount.value > 0) {
    return `其中 ${scopeMissingCount.value} 条已不在待收货列表，可能已收货或已被清理。`
  }

  return '你现在可以在当前范围内继续筛选、单条确认或批量收货。'
})

function formatCurrency(value?: string | number | null) {
  if (value == null || value === '') {
    return '--'
  }

  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return '--'
  }

  return `¥${numericValue.toFixed(2)}`
}

const filteredPendingReceipts = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()

  return scopedPendingReceipts.value.filter((item) => {
    const matchesKeyword =
      !keyword ||
      item.material_name.toLowerCase().includes(keyword) ||
      (item.specification ?? '').toLowerCase().includes(keyword) ||
      (item.supplier_name ?? '').toLowerCase().includes(keyword) ||
      (item.requester ?? '').toLowerCase().includes(keyword) ||
      (item.location_name ?? '').toLowerCase().includes(keyword)

    const matchesLocation = !locationMissingOnly.value || !(item.location_name ?? '').trim()
    return matchesKeyword && matchesLocation
  })
})
const allPendingIds = computed(() => filteredPendingReceipts.value.map((item) => item.purchase_item_id))
const selectedPendingDeleteIds = computed(() => allPendingIds.value.filter((itemId) => selectedItemIds.value.includes(itemId)))
const allPendingSelected = computed(
  () => allPendingIds.value.length > 0 && selectedPendingDeleteIds.value.length === allPendingIds.value.length,
)
const hasSelectedPendingItems = computed(() => selectedItemIds.value.length > 0)
const selectedPendingReceipts = computed(() =>
  pendingReceipts.value.filter((item) => selectedItemIds.value.includes(item.purchase_item_id)),
)
const singleQuantityError = computed(() => {
  if (receiveMode.value !== 'single') {
    return ''
  }

  const quantity = Number(receiptForm.value.quantity || 0)
  if (quantity <= 0) {
    return '收货数量必须大于 0。'
  }

  const pendingQuantity = Number(selectedPendingReceipt.value?.pending_quantity ?? 0)
  if (selectedPendingReceipt.value && quantity > pendingQuantity) {
    return `收货数量不能超过待收数量 ${pendingQuantity}。`
  }

  return ''
})
const occurredOnError = computed(() => (receiptForm.value.occurred_on ? '' : '请选择收货日期。'))
const amountError = computed(() => {
  const amount = receiptForm.value.total_amount
  if (amount == null || (typeof amount === 'number' && Number.isNaN(amount))) {
    return ''
  }

  return Number(amount) >= 0 ? '' : '金额不能小于 0。'
})
const batchSummary = computed(() => {
  const totalQuantity = selectedPendingReceipts.value.reduce((sum, item) => sum + Number(item.pending_quantity || 0), 0)
  const uniqueSuppliers = [...new Set(selectedPendingReceipts.value.map((item) => item.supplier_name?.trim()).filter(Boolean))]
  const uniqueLocations = [...new Set(selectedPendingReceipts.value.map((item) => item.location_name?.trim()).filter(Boolean))]
  const previewItems = selectedPendingReceipts.value.slice(0, 4).map((item) => `${item.material_name} × ${item.pending_quantity}${item.unit || '件'}`)
  return {
    itemCount: selectedPendingReceipts.value.length,
    totalQuantity: Number(totalQuantity.toFixed(2)),
    supplierSummary: uniqueSuppliers.length ? uniqueSuppliers.slice(0, 2).join('、') : '未填供应商',
    supplierCount: uniqueSuppliers.length,
    locationCount: uniqueLocations.length,
    previewItems,
    remainingPreviewCount: Math.max(selectedPendingReceipts.value.length - previewItems.length, 0),
  }
})
const submitDisabled = computed(() => {
  if (receiving.value || Boolean(occurredOnError.value)) {
    return true
  }

  if (receiveMode.value === 'batch') {
    return !selectedPendingReceipts.value.length
  }

  return !selectedPendingReceipt.value || Boolean(singleQuantityError.value)
})

function syncReceiptForm(item: PurchasePendingReceipt) {
  choosePendingReceipt(item)
  receiptForm.value.purchase_item_id = item.purchase_item_id
  receiptForm.value.quantity = Number(item.pending_quantity)
  receiptForm.value.total_amount = item.total_amount == null ? null : Number(item.total_amount)
  receiptForm.value.item_code = item.item_code ?? ''
  receiptForm.value.supplier_name = item.supplier_name ?? ''
  receiptForm.value.location_name = item.location_name ?? ''
  receiptForm.value.notes = `${item.material_name} 收货`
}

function clearSingleSelection() {
  choosePendingReceipt(null)
  receiptForm.value.purchase_item_id = 0
  receiptForm.value.quantity = 1
  receiptForm.value.total_amount = null
  receiptForm.value.item_code = ''
  receiptForm.value.supplier_name = ''
  receiptForm.value.location_name = ''
  receiptForm.value.notes = ''
}

function toggleItemSelection(itemId: number) {
  if (selectedItemIds.value.includes(itemId)) {
    selectedItemIds.value = selectedItemIds.value.filter((id) => id !== itemId)
    return
  }

  selectedItemIds.value = [...selectedItemIds.value, itemId]
}

function toggleSelectAllPending() {
  if (allPendingSelected.value) {
    selectedItemIds.value = selectedItemIds.value.filter((id) => !allPendingIds.value.includes(id))
    return
  }

  selectedItemIds.value = [...new Set([...selectedItemIds.value, ...allPendingIds.value])]
}

function resetBatchDraft() {
  receiptForm.value.purchase_item_id = 0
  receiptForm.value.quantity = 1
  receiptForm.value.total_amount = null
  receiptForm.value.item_code = ''
  receiptForm.value.supplier_name = ''
  receiptForm.value.location_name = ''
  receiptForm.value.notes = ''
}

function switchReceiveMode(mode: ReceiveMode) {
  receiveMode.value = mode
  if (mode === 'batch') {
    resetBatchDraft()
    return
  }

  if (mode === 'single') {
    selectedItemIds.value = []
    if (selectedPendingReceipt.value) {
      syncReceiptForm(selectedPendingReceipt.value)
    }
  }
}

function syncRouteSelection() {
  const queryId = Number(route.query.purchaseItemId)
  const targetId =
    Number.isFinite(queryId) && queryId > 0
      ? queryId
      : scopedPurchaseItemIds.value.length === 1
        ? scopedPurchaseItemIds.value[0]
        : 0

  if (!targetId) {
    if (
      selectedPendingReceipt.value &&
      scopedPurchaseItemIds.value.length &&
      !scopedPurchaseItemIds.value.includes(selectedPendingReceipt.value.purchase_item_id)
    ) {
      clearSingleSelection()
    }
    return
  }

  const matchedItem = pendingReceipts.value.find((item) => item.purchase_item_id === targetId)
  if (matchedItem) {
    switchReceiveMode('single')
    syncReceiptForm(matchedItem)
  }
}

async function handleBulkDelete() {
  if (!selectedItemIds.value.length) {
    ElMessage.warning('请先勾选要删除的采购明细。')
    return
  }

  try {
    await ElMessageBox.confirm(
      `将删除 ${selectedItemIds.value.length} 条待收货采购明细。此操作仅建议在测试阶段使用。`,
      '确认删除采购明细',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    const response = await deletePendingPurchaseItems(selectedItemIds.value)
    selectedItemIds.value = selectedItemIds.value.filter((id) => !response.deleted_item_ids.includes(id))
    await Promise.all([loadPendingReceipts(), loadDashboard({ quiet: true })])

    if (selectedPendingReceipt.value) {
      const nextSelected = pendingReceipts.value.find((item) => item.purchase_item_id === selectedPendingReceipt.value?.purchase_item_id)
      if (!nextSelected) {
        clearSingleSelection()
      }
    }

    syncRouteSelection()
    ElMessage.success(`已删除 ${response.deleted_count} 条采购明细。`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '删除采购明细失败'
    ElMessage.error(message)
  } finally {
    deleting.value = false
  }
}

async function submitBatchReceipt() {
  if (!selectedPendingReceipts.value.length) {
    ElMessage.warning('请先勾选要批量收货的采购明细。')
    return
  }

  if (occurredOnError.value) {
    ElMessage.warning(occurredOnError.value)
    return
  }

  if (amountError.value) {
    ElMessage.warning(amountError.value)
    return
  }

  const locationStrategy = receiptForm.value.location_name?.trim()
    ? `统一区位：${receiptForm.value.location_name.trim()}`
    : '统一区位：本次未填写，将沿用各明细当前区位；新建库存项时保持为空'
  const previewSummary = batchSummary.value.previewItems.join('；')
  const remainingSummary = batchSummary.value.remainingPreviewCount > 0 ? `；其余 ${batchSummary.value.remainingPreviewCount} 条将按同样规则执行` : ''

  try {
    await ElMessageBox.confirm(
      [
        `本次将一次性收货 ${batchSummary.value.itemCount} 条采购明细，合计待收数量 ${batchSummary.value.totalQuantity}。`,
        `涉及供应商：${batchSummary.value.supplierSummary}${batchSummary.value.supplierCount > 2 ? ` 等 ${batchSummary.value.supplierCount} 个` : ''}`,
        `收货日期：${receiptForm.value.occurred_on}`,
        locationStrategy,
        `操作人：${receiptForm.value.operator_name?.trim() || '未填写'}`,
        `示例明细：${previewSummary || '未选择明细'}${remainingSummary}`,
      ].join('\n'),
      '确认批量收货',
      {
        confirmButtonText: '确认入库',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  receiving.value = true

  const successItems: string[] = []
  const failedItems: string[] = []

  try {
    for (const item of selectedPendingReceipts.value) {
      try {
        await receivePurchaseItem({
          purchase_item_id: item.purchase_item_id,
          quantity: Number(item.pending_quantity),
          occurred_on: receiptForm.value.occurred_on,
          supplier_name: receiptForm.value.supplier_name?.trim() || item.supplier_name?.trim() || undefined,
          location_name: receiptForm.value.location_name?.trim() || undefined,
          operator_name: receiptForm.value.operator_name?.trim() || undefined,
          reference_code: receiptForm.value.reference_code?.trim() || undefined,
          notes: receiptForm.value.notes?.trim() || `${item.material_name} 收货`,
        })
        successItems.push(`${item.material_name} × ${item.pending_quantity}${item.unit || '件'}`)
      } catch (error) {
        const message = error instanceof Error ? error.message : '未知错误'
        failedItems.push(`${item.material_name}: ${message}`)
      }
    }

    await Promise.all([loadDashboard({ quiet: true }), loadPendingReceipts()])
    selectedItemIds.value = selectedPendingReceipts.value
      .map((item) => item.purchase_item_id)
      .filter((itemId) => pendingReceipts.value.some((item) => item.purchase_item_id === itemId))

    if (successItems.length) {
      ElMessage.success(`已完成 ${successItems.length} 条采购明细的批量收货。`)
    }

    if (failedItems.length) {
      await ElMessageBox.alert(
        [`成功 ${successItems.length} 条`, `失败 ${failedItems.length} 条`, '', ...failedItems].join('\n'),
        '批量收货结果',
        {
          confirmButtonText: '知道了',
        },
      )
    }
  } finally {
    receiving.value = false
  }
}

async function submitSingleReceipt() {
  if (!receiptForm.value.purchase_item_id) {
    ElMessage.warning('请先选择一条待收货采购明细。')
    return
  }

  if (singleQuantityError.value) {
    ElMessage.warning(singleQuantityError.value)
    return
  }

  if (occurredOnError.value) {
    ElMessage.warning(occurredOnError.value)
    return
  }

  if (amountError.value) {
    ElMessage.warning(amountError.value)
    return
  }

  receiving.value = true
  try {
    await receivePurchaseItem({
      ...receiptForm.value,
      total_amount: receiptForm.value.total_amount == null ? null : Number(receiptForm.value.total_amount),
      supplier_name: receiptForm.value.supplier_name?.trim() || undefined,
      location_name: receiptForm.value.location_name?.trim() || undefined,
      operator_name: receiptForm.value.operator_name?.trim() || undefined,
      reference_code: receiptForm.value.reference_code?.trim() || undefined,
      notes: receiptForm.value.notes?.trim() || undefined,
      item_code: receiptForm.value.item_code?.trim() || undefined,
    })
    ElMessage.success('采购收货已入库。')
    await Promise.all([loadDashboard({ quiet: true }), loadPendingReceipts()])

    const currentId = selectedPendingReceiptId.value
    const nextReceipt = pendingReceipts.value.find((item) => item.purchase_item_id === currentId)
    if (nextReceipt) {
      syncReceiptForm(nextReceipt)
    } else {
      clearSingleSelection()
      syncRouteSelection()
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '采购收货失败'
    ElMessage.error(message)
  } finally {
    receiving.value = false
  }
}

async function submitPurchaseReceipt() {
  if (receiveMode.value === 'batch') {
    await submitBatchReceipt()
    return
  }

  await submitSingleReceipt()
}

watch(pendingReceipts, (items) => {
  const currentIds = new Set(items.map((item) => item.purchase_item_id))
  selectedItemIds.value = selectedItemIds.value.filter((id) => currentIds.has(id))
  syncRouteSelection()
})

watch(
  () => [route.query.purchaseItemId, route.query.purchaseItemIds],
  () => {
    syncRouteSelection()
  },
)

onMounted(async () => {
  await Promise.all([loadDashboard(), loadPendingReceipts()])
  syncRouteSelection()
})
</script>

<template>
  <div class="page-stack purchase-receiving-task-page">
    <div class="content-grid">
      <section class="page-section purchase-receiving-list-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">采购收货</p>
            <h3>{{ receiveMode === 'single' ? '先选待收货明细，再确认单条入库' : '先圈定待收货范围，再统一批量入库' }}</h3>
          </div>
          <span class="section-meta">
            {{ pendingReceiptsLoading ? '加载中' : `${filteredPendingReceipts.length} / ${scopedPendingReceipts.length} 条待收货` }}
          </span>
        </div>

        <div class="segment-switch receiving-mode-switch">
          <button class="segment-chip" :class="{ active: receiveMode === 'single' }" type="button" @click="switchReceiveMode('single')">
            单条收货
          </button>
          <button class="segment-chip" :class="{ active: receiveMode === 'batch' }" type="button" @click="switchReceiveMode('batch')">
            批量收货
          </button>
        </div>

        <div class="toolbar-grid compact-toolbar receiving-filter-toolbar">
          <label class="field">
            <span>搜索待收货</span>
            <input v-model="searchKeyword" type="text" placeholder="按物料、规格、供应商、请购人、区位搜索" />
          </label>

          <button
            class="soft-button"
            :class="{ active: locationMissingOnly }"
            type="button"
            @click="locationMissingOnly = !locationMissingOnly"
          >
            {{ locationMissingOnly ? '当前只看未填区位' : '只看未填区位' }}
          </button>
        </div>

        <div class="status-strip workflow-strip receiving-context-strip">
          <div>
            <span>当前范围</span>
            <strong>{{ scopedPurchaseItemIds.length ? scopeTitle : '全部待收货' }}</strong>
            <small>
              {{
                scopedPurchaseItemIds.length
                  ? scopeDescription
                  : '当前可查看全部待收货，并继续按关键词或区位状态筛选。'
              }}
            </small>
          </div>
          <div>
            <span>当前处理对象</span>
            <strong>{{ receiveMode === 'batch' ? `${selectedItemIds.length} 条待收货` : selectedPendingReceipt?.material_name || '未选择' }}</strong>
            <small>
              {{
                receiveMode === 'batch'
                  ? '批量模式仅对当前勾选明细生效。'
                  : selectedPendingReceipt ? `采购明细 #${selectedPendingReceipt.purchase_item_id}` : '从列表点击一条待收货明细开始。'
              }}
            </small>
          </div>
          <div>
            <span>执行规则</span>
            <strong>{{ receiveMode === 'batch' ? '按待收数量一次收货' : '允许按到货数量部分收货' }}</strong>
            <small>{{ receiveMode === 'batch' ? '确认后逐条入库，并保留统一日期与可选覆盖字段。' : '数量不可超过当前待收数量。' }}</small>
          </div>
        </div>

        <div class="inline-summary-row receiving-workspace-row">
          <span>库存项目 <strong>{{ dashboard?.summary.total_items ?? '--' }}</strong></span>
          <span>库存总量 <strong>{{ dashboard?.summary.total_stock_quantity ?? '--' }}</strong></span>
          <span>待处理采购 <strong>{{ dashboard?.summary.pending_purchase_orders ?? '--' }}</strong></span>
          <RouterLink v-if="scopedPurchaseItemIds.length" class="action-link ghost" to="/purchase-receiving">查看全部待收货</RouterLink>
        </div>

        <div v-if="receiveMode === 'batch'" class="selection-toolbar">
          <label class="checkbox-chip">
            <input :checked="allPendingSelected" type="checkbox" @change="toggleSelectAllPending" />
            <span>全选当前筛选结果</span>
          </label>

          <div class="selection-actions">
            <span>{{ selectedItemIds.length }} 项已勾选</span>
            <span>确认后会按勾选范围统一执行批量收货</span>
          </div>
        </div>

        <div v-if="receiveMode === 'batch' && selectedPendingReceipts.length" class="inline-summary-row receiving-selection-row">
          <span>已勾选 <strong>{{ batchSummary.itemCount }} 条</strong></span>
          <span>待收总量 <strong>{{ batchSummary.totalQuantity }}</strong></span>
          <span>
            涉及供应商
            <strong>
              {{ batchSummary.supplierSummary }}<template v-if="batchSummary.supplierCount > 2"> 等 {{ batchSummary.supplierCount }} 个</template>
            </strong>
          </span>
          <span>
            涉及区位
            <strong>{{ batchSummary.locationCount > 1 ? `${batchSummary.locationCount} 个` : '单一区位或未填' }}</strong>
          </span>
        </div>

        <p v-if="receiveMode === 'batch' && selectedPendingReceipts.length" class="field-hint receiving-selection-note">
          示例明细：{{ batchSummary.previewItems.join('；') || '先从左侧勾选待收货明细' }}<template v-if="batchSummary.remainingPreviewCount">；其余 {{ batchSummary.remainingPreviewCount }} 条</template>
        </p>

        <div class="console-table desktop-only ledger-window">
          <div class="console-table-scroll">
            <table class="console-data-table dense-table receiving-data-table">
              <colgroup>
                <col style="width: 72px" />
                <col style="width: 250px" />
                <col style="width: 180px" />
                <col style="width: 180px" />
                <col style="width: 130px" />
                <col style="width: 150px" />
                <col style="width: 120px" />
                <col style="width: 120px" />
                <col style="width: 110px" />
                <col style="width: 110px" />
              </colgroup>
              <thead>
                <tr>
                  <th class="console-data-head center">选择</th>
                  <th>物料名称</th>
                  <th>规格</th>
                  <th>供应商</th>
                  <th>请购人</th>
                  <th>区位</th>
                  <th class="align-right">待收数量</th>
                  <th class="align-right">已收数量</th>
                  <th class="align-right">金额</th>
                  <th class="align-right">到货日期</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in filteredPendingReceipts"
                  :key="item.purchase_item_id"
                  :data-purchase-item-id="item.purchase_item_id"
                  class="console-data-row interactive"
                  :class="{
                    active:
                      receiveMode === 'single'
                        ? item.purchase_item_id === selectedPendingReceiptId
                        : selectedItemIds.includes(item.purchase_item_id),
                  }"
                  @click="receiveMode === 'single' ? syncReceiptForm(item) : toggleItemSelection(item.purchase_item_id)"
                >
                  <td class="console-data-cell center v-middle">
                    <label v-if="receiveMode === 'batch'" class="console-checkbox" @click.stop>
                      <input
                        :checked="selectedItemIds.includes(item.purchase_item_id)"
                        type="checkbox"
                        @change="toggleItemSelection(item.purchase_item_id)"
                      />
                    </label>
                    <span v-else :class="['console-badge', item.purchase_item_id === selectedPendingReceiptId ? 'ok' : 'neutral']">
                      {{ item.purchase_item_id === selectedPendingReceiptId ? '已选' : '待选' }}
                    </span>
                  </td>
                  <td class="console-data-cell">
                    <div class="console-cell">
                      <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
                      <small class="console-subline">#{{ item.purchase_item_id }}</small>
                    </div>
                  </td>
                  <td class="console-data-cell">
                    <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
                  </td>
                  <td class="console-data-cell">
                    <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填供应商'">{{ item.supplier_name || '未填供应商' }}</div>
                  </td>
                  <td class="console-data-cell">
                    <div class="console-cell muted console-nowrap" :title="item.requester || '未填请购人'">{{ item.requester || '未填请购人' }}</div>
                  </td>
                  <td class="console-data-cell">
                    <div class="console-cell muted console-nowrap" :title="item.location_name || '未填区位'">{{ item.location_name || '未填区位' }}</div>
                  </td>
                  <td class="console-data-cell align-right v-middle">
                    <div class="console-cell align-right">
                      <span class="console-badge info">{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
                    </div>
                  </td>
                  <td class="console-data-cell align-right v-middle">
                    <div class="console-cell muted console-nowrap align-right">{{ item.received_quantity }} {{ item.unit || '件' }}</div>
                  </td>
                  <td class="console-data-cell align-right v-middle">
                    <div class="console-cell muted console-nowrap align-right" :title="formatCurrency(item.total_amount)">{{ formatCurrency(item.total_amount) }}</div>
                  </td>
                  <td class="console-data-cell align-right v-middle">
                    <div class="console-cell muted console-nowrap align-right" :title="item.expected_arrival || '未记录'">{{ item.expected_arrival || '未记录' }}</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="pendingReceiptsLoading" class="console-empty">正在加载待收货明细...</div>
          <div v-else-if="!filteredPendingReceipts.length" class="console-empty">
            {{ scopedPendingReceipts.length ? '当前筛选条件下没有匹配明细。' : '当前没有待收货采购明细。' }}
          </div>
        </div>

        <div class="mobile-only mobile-flow-stack">
          <div class="stack-list">
            <article
              v-for="item in filteredPendingReceipts"
              :key="item.purchase_item_id"
              class="data-row clickable triplet receipt-card mobile-task-card"
              role="button"
              tabindex="0"
              :class="{
                active:
                  receiveMode === 'single'
                    ? item.purchase_item_id === selectedPendingReceiptId
                    : selectedItemIds.includes(item.purchase_item_id),
              }"
              @click="receiveMode === 'single' ? syncReceiptForm(item) : toggleItemSelection(item.purchase_item_id)"
              @keydown.enter.prevent="receiveMode === 'single' ? syncReceiptForm(item) : toggleItemSelection(item.purchase_item_id)"
              @keydown.space.prevent="receiveMode === 'single' ? syncReceiptForm(item) : toggleItemSelection(item.purchase_item_id)"
            >
              <div v-if="receiveMode === 'batch'" class="row-checkbox" @click.stop>
                <input
                  :checked="selectedItemIds.includes(item.purchase_item_id)"
                  type="checkbox"
                  @change="toggleItemSelection(item.purchase_item_id)"
                />
              </div>

              <div class="data-row-main">
                <div class="data-row-head">
                  <strong>{{ item.material_name }}</strong>
                  <span class="data-row-badge">{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
                </div>
                <div class="data-row-meta">
                  <span>规格：{{ item.specification || '未填规格' }}</span>
                  <span>供应商：{{ item.supplier_name || '未填供应商' }}</span>
                  <span>请购人：{{ item.requester || '未填' }}</span>
                  <span>金额：{{ formatCurrency(item.total_amount) }}</span>
                  <span>区位：{{ item.location_name || '未填区位' }}</span>
                  <span>已收：{{ item.received_quantity }} {{ item.unit || '件' }}</span>
                  <span>到货：{{ item.expected_arrival || '未记录' }}</span>
                </div>
              </div>
            </article>

            <div v-if="pendingReceiptsLoading" class="empty-state">正在加载待收货明细...</div>
            <div v-else-if="!filteredPendingReceipts.length" class="empty-state">
              {{ scopedPendingReceipts.length ? '当前筛选条件下没有匹配明细。' : '当前没有待收货采购明细。' }}
            </div>
          </div>
        </div>

        <details v-if="receiveMode === 'batch'" class="test-tools-panel receiving-maintenance-panel">
          <summary>开发测试清理 <small>{{ selectedItemIds.length }} 项已勾选</small></summary>
          <div class="selection-toolbar selection-toolbar-inline">
            <div class="selection-status">
              <span>危险操作</span>
              <strong>删除当前勾选的待收货明细</strong>
              <small>只建议在测试环境清理数据时使用，不属于正常采购收货流程。</small>
            </div>

            <div class="selection-actions">
              <button class="danger-button" :disabled="deleting || !hasSelectedPendingItems" type="button" @click="handleBulkDelete">
                {{ deleting ? '删除中...' : '删除勾选明细' }}
              </button>
            </div>
          </div>
        </details>
      </section>

      <section class="page-section purchase-receiving-form-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">执行收货</p>
            <h3>
              {{
                receiveMode === 'batch'
                  ? `批量收货 ${batchSummary.itemCount} 条明细`
                  : selectedPendingReceipt?.material_name || '请选择待收货明细'
              }}
            </h3>
          </div>
          <span class="section-meta">{{ receiveMode === 'batch' ? '批量模式需要显式勾选' : '单条模式按明细确认' }}</span>
        </div>

        <div class="receipt-summary emphasis-summary">
          <template v-if="receiveMode === 'batch'">
            <div class="inline-summary-row receiving-form-inline-summary">
              <span>已勾选 <strong>{{ batchSummary.itemCount }} 条</strong></span>
              <span>待收总量 <strong>{{ batchSummary.totalQuantity }}</strong></span>
              <span>
                涉及供应商
                <strong>
                  {{ batchSummary.supplierSummary }}<template v-if="batchSummary.supplierCount > 2"> 等 {{ batchSummary.supplierCount }} 个</template>
                </strong>
              </span>
              <span>统一区位 <strong>{{ receiptForm.location_name || '沿用原区位' }}</strong></span>
            </div>
            <p class="field-hint receiving-form-note">
              示例明细：{{ batchSummary.previewItems.join('；') || '先从左侧勾选待收货明细' }}<template v-if="batchSummary.remainingPreviewCount">；其余 {{ batchSummary.remainingPreviewCount }} 条</template>
            </p>
          </template>
          <template v-else>
            <div class="inline-summary-row receiving-form-inline-summary">
              <span>供应商 <strong>{{ receiptForm.supplier_name || selectedPendingReceipt?.supplier_name || '未填' }}</strong></span>
              <span>请购人 <strong>{{ selectedPendingReceipt?.requester || '未填' }}</strong></span>
              <span>当前区位 <strong>{{ selectedPendingReceipt?.location_name || '未填' }}</strong></span>
              <span>
                已收 / 待收
                <strong>{{ selectedPendingReceipt?.received_quantity || '0' }} / {{ selectedPendingReceipt?.pending_quantity || '-' }} {{ selectedPendingReceipt?.unit || '件' }}</strong>
              </span>
            </div>
            <div class="inline-summary-row receiving-form-inline-summary">
              <span>物品编号 <strong>{{ receiptForm.item_code || selectedPendingReceipt?.item_code || '未填' }}</strong></span>
              <span>本次金额 <strong>{{ formatCurrency(receiptForm.total_amount) }}</strong></span>
              <span>
                请购数量
                <strong>{{ selectedPendingReceipt?.requested_quantity || '-' }} {{ selectedPendingReceipt?.unit || '件' }}</strong>
              </span>
            </div>
          </template>
        </div>

        <form class="form-stack" @submit.prevent="submitPurchaseReceipt">
          <div class="toolbar-grid dual receiving-form-grid">
            <label v-if="receiveMode === 'single'" class="field">
              <span>本次收货数量</span>
              <input v-model.number="receiptForm.quantity" min="0.01" step="0.01" type="number" inputmode="decimal" />
              <small v-if="singleQuantityError" class="field-hint danger">{{ singleQuantityError }}</small>
            </label>

            <label v-if="receiveMode === 'single'" class="field">
              <span>本次金额</span>
              <input v-model.number="receiptForm.total_amount" min="0" step="0.01" type="number" inputmode="decimal" placeholder="例如 128.50" />
              <small v-if="amountError" class="field-hint danger">{{ amountError }}</small>
            </label>

            <label class="field">
              <span>{{ receiveMode === 'batch' ? '统一收货日期' : '收货日期' }}</span>
              <input v-model="receiptForm.occurred_on" type="date" />
              <small v-if="occurredOnError" class="field-hint danger">{{ occurredOnError }}</small>
            </label>
          </div>

          <div class="toolbar-grid dual receiving-form-grid">
            <label v-if="receiveMode === 'single'" class="field">
              <span>物品编号</span>
              <input v-model="receiptForm.item_code" type="text" placeholder="例如 SKU-20260606-01" />
            </label>

            <label class="field">
              <span>{{ receiveMode === 'batch' ? '统一供应商' : '供应商' }}</span>
              <input
                v-model="receiptForm.supplier_name"
                type="text"
                :placeholder="receiveMode === 'batch' ? '留空则沿用各明细原供应商' : '例如 深圳某某电子'"
              />
            </label>

            <label class="field">
              <span>{{ receiveMode === 'batch' ? '统一区位' : '区位' }}</span>
              <input v-model="receiptForm.location_name" type="text" placeholder="例如 A-01-03" />
            </label>
          </div>

          <div class="toolbar-grid dual receiving-form-grid">
            <label class="field">
              <span>操作人</span>
              <input v-model="receiptForm.operator_name" type="text" placeholder="仓管员" />
            </label>

            <label class="field">
              <span>入库单号</span>
              <input v-model="receiptForm.reference_code" type="text" placeholder="例如 RK-PO-20260530-01" />
            </label>
          </div>

          <label class="field">
            <span>备注</span>
            <textarea
              v-model="receiptForm.notes"
              rows="4"
              :placeholder="receiveMode === 'batch' ? '批量收货说明，将复用于每条明细' : '收货说明'"
            ></textarea>
          </label>

          <button class="primary-button" :disabled="submitDisabled" type="submit">
            {{
              receiving
                ? '入库中...'
                : receiveMode === 'batch'
                  ? `确认批量收货 ${batchSummary.itemCount} 条`
                  : '确认收货入库'
            }}
          </button>
        </form>
      </section>
    </div>
  </div>
</template>
