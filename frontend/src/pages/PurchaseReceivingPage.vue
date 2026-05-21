<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'
import { deletePendingPurchaseItems, receivePurchaseItem } from '../services/api'
import type { PurchasePendingReceipt, PurchaseReceivePayload } from '../types/inventory'

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
const selectedItemIds = ref<number[]>([])
const receiptForm = ref<PurchaseReceivePayload>({
  purchase_item_id: 0,
  quantity: 1,
  occurred_on: new Date().toISOString().slice(0, 10),
  operator_name: '',
  reference_code: 'RK-PO-',
  notes: '',
})

const allPendingIds = computed(() => pendingReceipts.value.map((item) => item.purchase_item_id))
const selectedPendingDeleteIds = computed(() => allPendingIds.value.filter((itemId) => selectedItemIds.value.includes(itemId)))
const allPendingSelected = computed(
  () => allPendingIds.value.length > 0 && selectedPendingDeleteIds.value.length === allPendingIds.value.length,
)
const hasSelectedPendingItems = computed(() => selectedItemIds.value.length > 0)
const selectedPendingReceipts = computed(() =>
  pendingReceipts.value.filter((item) => selectedItemIds.value.includes(item.purchase_item_id)),
)
const isBatchReceiveMode = computed(() => selectedPendingReceipts.value.length > 0)

function syncReceiptForm(item: PurchasePendingReceipt) {
  choosePendingReceipt(item)
  receiptForm.value.purchase_item_id = item.purchase_item_id
  receiptForm.value.quantity = Number(item.pending_quantity)
  receiptForm.value.notes = `${item.material_name} 收货`
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
      syncReceiptForm(selectedPendingReceipt.value)
    } else {
      receiptForm.value.purchase_item_id = 0
    }

    ElMessage.success(`已删除 ${response.deleted_count} 条采购明细。`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '删除采购明细失败'
    ElMessage.error(message)
  } finally {
    deleting.value = false
  }
}

async function submitPurchaseReceipt() {
  if (isBatchReceiveMode.value) {
    receiving.value = true
    try {
      for (const item of selectedPendingReceipts.value) {
        await receivePurchaseItem({
          purchase_item_id: item.purchase_item_id,
          quantity: Number(item.pending_quantity),
          occurred_on: receiptForm.value.occurred_on,
          operator_name: receiptForm.value.operator_name,
          reference_code: receiptForm.value.reference_code,
          notes: receiptForm.value.notes?.trim() || `${item.material_name} 收货`,
        })
      }

      ElMessage.success(`已批量入库 ${selectedPendingReceipts.value.length} 条采购明细。`)
      selectedItemIds.value = []
      await Promise.all([loadDashboard({ quiet: true }), loadPendingReceipts()])

      const nextReceipt = pendingReceipts.value[0]
      if (nextReceipt) {
        syncReceiptForm(nextReceipt)
      } else {
        receiptForm.value.purchase_item_id = 0
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '批量采购收货失败'
      ElMessage.error(message)
    } finally {
      receiving.value = false
    }
    return
  }

  if (!receiptForm.value.purchase_item_id) {
    ElMessage.warning('请先选择一条待收货采购明细。')
    return
  }

  receiving.value = true
  try {
    await receivePurchaseItem(receiptForm.value)
    ElMessage.success('采购收货已入库。')
    await Promise.all([loadDashboard({ quiet: true }), loadPendingReceipts()])

    const nextReceipt = pendingReceipts.value.find((item) => item.purchase_item_id === selectedPendingReceiptId.value) ?? pendingReceipts.value[0]
    if (nextReceipt) {
      syncReceiptForm(nextReceipt)
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '采购收货失败'
    ElMessage.error(message)
  } finally {
    receiving.value = false
  }
}

watch(pendingReceipts, (items) => {
  const currentIds = new Set(items.map((item) => item.purchase_item_id))
  selectedItemIds.value = selectedItemIds.value.filter((id) => currentIds.has(id))
})

onMounted(async () => {
  await Promise.all([loadDashboard(), loadPendingReceipts()])
  if (pendingReceipts.value[0]) {
    syncReceiptForm(pendingReceipts.value[0])
  }
})
</script>

<template>
  <div class="page-stack">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">采购入账</p>
          <h3>待收货明细直达库存</h3>
        </div>
        <span class="section-meta">{{ pendingReceiptsLoading ? '加载中' : `${pendingReceipts.length} 条待收货` }}</span>
      </div>

      <div class="link-row">
        <RouterLink class="action-link ghost" to="/purchase-import">先做采购导入</RouterLink>
      </div>

      <div class="metric-grid compact">
        <article class="metric-card">
          <span>库存项目</span>
          <strong>{{ dashboard?.summary.total_items ?? '--' }}</strong>
        </article>
        <article class="metric-card">
          <span>库存总量</span>
          <strong>{{ dashboard?.summary.total_stock_quantity ?? '--' }}</strong>
        </article>
        <article class="metric-card accent">
          <span>待处理采购</span>
          <strong>{{ dashboard?.summary.pending_purchase_orders ?? '--' }}</strong>
        </article>
      </div>
    </section>

    <div class="content-grid">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">待收货列表</p>
            <h3>先选采购明细</h3>
          </div>
          <span class="section-meta">最多展示 40 条</span>
        </div>

        <div class="selection-toolbar">
          <label class="checkbox-chip">
            <input :checked="allPendingSelected" type="checkbox" @change="toggleSelectAllPending" />
            <span>全选当前待收货列表</span>
          </label>

          <div class="selection-actions">
            <span>{{ selectedItemIds.length }} 项已勾选</span>
            <button class="danger-button" :disabled="deleting || !hasSelectedPendingItems" type="button" @click="handleBulkDelete">
              {{ deleting ? '删除中...' : '删除勾选采购明细' }}
            </button>
          </div>
        </div>

        <div class="stack-list">
          <article
            v-for="item in pendingReceipts"
            :key="item.purchase_item_id"
            class="data-row clickable triplet receipt-card"
            :class="{ active: item.purchase_item_id === selectedPendingReceiptId }"
            @click="syncReceiptForm(item)"
          >
            <div class="row-checkbox" @click.stop>
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
                <span>供应商：{{ item.supplier_name || '未填供应商' }}</span>
                <span>请购人：{{ item.requester || '未填' }}</span>
                <span>规格：{{ item.specification || '未填规格' }}</span>
                <span>来源：{{ item.sheet_name }}</span>
                <span>到货：{{ item.expected_arrival || '未记录' }}</span>
              </div>
            </div>

          </article>

          <div v-if="pendingReceiptsLoading" class="empty-state">正在加载待收货明细...</div>
          <div v-else-if="!pendingReceipts.length" class="empty-state">当前没有待收货采购明细。</div>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">收货表单</p>
            <h3>{{ isBatchReceiveMode ? `批量入库 ${selectedPendingReceipts.length} 条明细` : selectedPendingReceipt?.material_name || '请选择待收货明细' }}</h3>
          </div>
          <span class="section-meta">{{ isBatchReceiveMode ? '按勾选明细统一入库' : '按采购明细入库' }}</span>
        </div>

        <div class="receipt-summary">
          <template v-if="isBatchReceiveMode">
            <p>已勾选明细：{{ selectedPendingReceipts.length }} 条</p>
            <p>待收数量：将按每条明细当前待收数量分别入库</p>
            <p>说明：将按每条明细当前待收数量分别入库。</p>
          </template>
          <template v-else>
            <p>供应商：{{ selectedPendingReceipt?.supplier_name || '未填' }}</p>
            <p>请购人：{{ selectedPendingReceipt?.requester || '未填' }}</p>
            <p>待收数量：{{ selectedPendingReceipt?.pending_quantity || '-' }} {{ selectedPendingReceipt?.unit || '件' }}</p>
          </template>
        </div>

        <form class="form-stack" @submit.prevent="submitPurchaseReceipt">
          <div class="toolbar-grid dual">
            <label v-if="!isBatchReceiveMode" class="field">
              <span>收货数量</span>
              <input v-model.number="receiptForm.quantity" min="0.01" step="0.01" type="number" />
            </label>

            <label class="field">
              <span>{{ isBatchReceiveMode ? '统一收货日期' : '收货日期' }}</span>
              <input v-model="receiptForm.occurred_on" type="date" />
            </label>
          </div>

          <div class="toolbar-grid dual">
            <label class="field">
              <span>操作人</span>
              <input v-model="receiptForm.operator_name" type="text" placeholder="仓管员" />
            </label>

            <label class="field">
              <span>入库单号</span>
              <input v-model="receiptForm.reference_code" type="text" placeholder="例如 RK-PO-01" />
            </label>
          </div>

          <label class="field">
            <span>备注</span>
            <textarea
              v-model="receiptForm.notes"
              rows="4"
              :placeholder="isBatchReceiveMode ? '批量收货说明，将复用于每条明细' : '收货说明'"
            ></textarea>
          </label>

          <button class="primary-button" :disabled="receiving || (!selectedPendingReceipt && !isBatchReceiveMode)" type="submit">
            {{
              receiving
                ? '入库中...'
                : isBatchReceiveMode
                  ? `将勾选的 ${selectedPendingReceipts.length} 条明细统一入库`
                  : '按采购明细入库'
            }}
          </button>
        </form>
      </section>
    </div>
  </div>
</template>
