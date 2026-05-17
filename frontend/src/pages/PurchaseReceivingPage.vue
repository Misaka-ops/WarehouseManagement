<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'
import { receivePurchaseItem } from '../services/api'
import type { PurchasePendingReceipt, PurchaseReceivePayload } from '../types/inventory'

const { dashboard, inventoryItems, loadDashboard } = useInventoryWorkspace()
const { choosePendingReceipt, loadPendingReceipts, pendingReceipts, pendingReceiptsLoading, selectedPendingReceipt, selectedPendingReceiptId } =
  usePendingReceipts()

const receiving = ref(false)
const receiptForm = ref<PurchaseReceivePayload>({
  purchase_item_id: 0,
  quantity: 1,
  occurred_on: new Date().toISOString().slice(0, 10),
  operator_name: '',
  reference_code: 'RK-PO-',
  notes: '',
})

const relatedInventoryItem = computed(
  () => inventoryItems.value.find((item) => item.id === selectedPendingReceipt.value?.inventory_item_id) ?? null,
)

function syncReceiptForm(item: PurchasePendingReceipt) {
  choosePendingReceipt(item)
  receiptForm.value.purchase_item_id = item.purchase_item_id
  receiptForm.value.quantity = Number(item.pending_quantity)
  receiptForm.value.notes = `${item.material_name} 收货`
}

async function submitPurchaseReceipt() {
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

        <div class="stack-list">
          <button
            v-for="item in pendingReceipts"
            :key="item.purchase_item_id"
            class="receipt-card"
            :class="{ active: item.purchase_item_id === selectedPendingReceiptId }"
            type="button"
            @click="syncReceiptForm(item)"
          >
            <div class="receipt-card-head">
              <strong>{{ item.material_name }}</strong>
              <span>{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
            </div>
            <p>{{ item.specification || '未填规格' }}</p>
            <small>{{ item.supplier_name || '未填供应商' }} / {{ item.sheet_name }}</small>
          </button>

          <div v-if="pendingReceiptsLoading" class="empty-state">正在加载待收货明细...</div>
          <div v-else-if="!pendingReceipts.length" class="empty-state">当前没有待收货采购明细。</div>
        </div>
      </section>

      <div class="page-stack">
        <section class="page-section">
          <div class="section-heading">
            <div>
              <p class="section-kicker">收货表单</p>
              <h3>{{ selectedPendingReceipt?.material_name || '请选择待收货明细' }}</h3>
            </div>
            <span class="section-meta">按采购明细入库</span>
          </div>

          <div class="receipt-summary">
            <p>供应商：{{ selectedPendingReceipt?.supplier_name || '未填' }}</p>
            <p>请购人：{{ selectedPendingReceipt?.requester || '未填' }}</p>
            <p>待收数量：{{ selectedPendingReceipt?.pending_quantity || '-' }} {{ selectedPendingReceipt?.unit || '件' }}</p>
          </div>

          <form class="form-stack" @submit.prevent="submitPurchaseReceipt">
            <div class="toolbar-grid dual">
              <label class="field">
                <span>收货数量</span>
                <input v-model.number="receiptForm.quantity" min="0.01" step="0.01" type="number" />
              </label>

              <label class="field">
                <span>收货日期</span>
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
              <textarea v-model="receiptForm.notes" rows="4" placeholder="收货说明"></textarea>
            </label>

            <button class="primary-button" :disabled="receiving || !selectedPendingReceipt" type="submit">
              {{ receiving ? '入库中...' : '按采购明细入库' }}
            </button>
          </form>
        </section>

        <section class="page-section">
          <div class="section-heading">
            <div>
              <p class="section-kicker">关联库存</p>
              <h3>{{ relatedInventoryItem?.material_name || '当前采购明细尚未关联库存项' }}</h3>
            </div>
            <span class="section-meta">收货后的落账位置</span>
          </div>

          <div v-if="relatedInventoryItem" class="stat-grid">
            <article class="stat-card">
              <span>当前库存</span>
              <strong>{{ relatedInventoryItem.quantity_on_hand }}</strong>
              <small>{{ relatedInventoryItem.unit || '件' }}</small>
            </article>
            <article class="stat-card">
              <span>规格型号</span>
              <strong class="minor">{{ relatedInventoryItem.specification || '未填' }}</strong>
            </article>
            <article class="stat-card">
              <span>供应商</span>
              <strong class="minor">{{ relatedInventoryItem.supplier_name || '未填' }}</strong>
            </article>
            <article class="stat-card">
              <span>最近入库</span>
              <strong class="minor">{{ relatedInventoryItem.last_receipt_at || '未记录' }}</strong>
            </article>
          </div>

          <div v-else class="empty-state">
            这条采购明细如果还没有对应库存项目，后端会在第一次收货时自动创建库存项。
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
