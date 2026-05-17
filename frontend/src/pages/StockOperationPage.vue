<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { postIssue, postReceipt } from '../services/api'
import type { InventoryItem, InventoryTransactionPayload } from '../types/inventory'

type TransactionMode = 'receipt' | 'issue'

const props = defineProps<{
  mode: TransactionMode
}>()

const { historyLoading, inventoryItems, itemTransactions, loading, loadDashboard, loadTransactions, selectItem, selectedItem, selectedItemId } =
  useInventoryWorkspace()

const searchKeyword = ref('')
const lowStockOnly = ref(false)
const submitting = ref(false)
const quickQuantities = [1, 5, 10, 20]

const form = ref<InventoryTransactionPayload>({
  item_id: 0,
  quantity: 1,
  occurred_on: new Date().toISOString().slice(0, 10),
  operator_name: '',
  reference_code: '',
  notes: '',
})

const isReceipt = computed(() => props.mode === 'receipt')
const pageLabel = computed(() => (isReceipt.value ? '入库登记' : '出库登记'))
const pageDescription = computed(() =>
  isReceipt.value
    ? '专注完成补货、返库和采购到货后的入账。'
    : '专注完成领料、发放和消耗出账。'
)
const submitLabel = computed(() => {
  if (submitting.value) {
    return '提交中...'
  }
  return isReceipt.value ? '确认入库' : '确认出库'
})
const referencePrefix = computed(() => (isReceipt.value ? 'RK-' : 'CK-'))
const alternateRoute = computed(() => (isReceipt.value ? '/issue' : '/receipt'))
const alternateLabel = computed(() => (isReceipt.value ? '切换到出库页面' : '切换到入库页面'))
const selectedStockQuantity = computed(() => Number(selectedItem.value?.quantity_on_hand ?? 0))
const issueBlockedReason = computed(() => {
  if (isReceipt.value || !selectedItem.value) {
    return ''
  }

  if (selectedStockQuantity.value <= 0) {
    return '当前物料库存为 0，不能执行出库。'
  }

  const requestedQuantity = Number(form.value.quantity || 0)
  if (requestedQuantity > selectedStockQuantity.value) {
    return `出库数量不能超过当前库存 ${selectedStockQuantity.value}。`
  }

  return ''
})
const submitDisabled = computed(() => submitting.value || !selectedItem.value || Boolean(issueBlockedReason.value))

const filteredItems = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()

  return inventoryItems.value.filter((item) => {
    const matchesKeyword =
      !keyword ||
      item.material_name.toLowerCase().includes(keyword) ||
      (item.specification ?? '').toLowerCase().includes(keyword) ||
      (item.supplier_name ?? '').toLowerCase().includes(keyword) ||
      (item.location_name ?? '').toLowerCase().includes(keyword)

    const matchesLowStock = !lowStockOnly.value || Number(item.quantity_on_hand) <= 5
    return matchesKeyword && matchesLowStock
  })
})

function applyQuickQuantity(quantity: number) {
  form.value.quantity = quantity
}

function nudgeQuantity(delta: number) {
  const nextValue = Math.max(0.01, Number(form.value.quantity || 0) + delta)
  form.value.quantity = Number(nextValue.toFixed(2))
}

function resetActionFields() {
  form.value.quantity = 1
  form.value.reference_code = referencePrefix.value
  form.value.notes = ''
}

function chooseInventoryItem(item: InventoryItem) {
  selectItem(item)
  form.value.item_id = item.id
}

async function submitTransaction() {
  if (!selectedItemId.value) {
    ElMessage.warning('请先选择一个库存项目。')
    return
  }

  if (issueBlockedReason.value) {
    ElMessage.warning(issueBlockedReason.value)
    return
  }

  submitting.value = true
  form.value.item_id = selectedItemId.value

  try {
    if (isReceipt.value) {
      await postReceipt(form.value)
      ElMessage.success('入库已登记。')
    } else {
      await postIssue(form.value)
      ElMessage.success('出库已登记。')
    }

    await loadDashboard({ quiet: true })
    await loadTransactions(selectedItemId.value)
    resetActionFields()
  } catch (error) {
    const message = axios.isAxiosError(error)
      ? (error.response?.data?.detail as string | undefined) || error.message || '提交失败'
      : error instanceof Error
        ? error.message
        : '提交失败'
    ElMessage.error(message)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  form.value.reference_code = referencePrefix.value
  await loadDashboard()
  if (!isReceipt.value) {
    const firstAvailableItem = inventoryItems.value.find((item) => Number(item.quantity_on_hand) > 0)
    if (firstAvailableItem) {
      chooseInventoryItem(firstAvailableItem)
    }
  }

  if (selectedItem.value) {
    form.value.item_id = selectedItem.value.id
  }
})
</script>

<template>
  <div class="content-grid">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">物料选择</p>
          <h3>{{ pageLabel }}</h3>
        </div>
        <span class="section-meta">{{ filteredItems.length }} / {{ inventoryItems.length }}</span>
      </div>

      <p class="section-copy tight">{{ pageDescription }}</p>

      <div class="toolbar-grid">
        <label class="field">
          <span>搜索</span>
          <input v-model="searchKeyword" type="text" placeholder="按物料、规格、供应商、区位搜索" />
        </label>

        <button class="soft-button" :class="{ active: lowStockOnly }" type="button" @click="lowStockOnly = !lowStockOnly">
          {{ lowStockOnly ? '只看低库存中' : '切到低库存' }}
        </button>
      </div>

      <div class="inventory-list">
        <article
          v-for="item in filteredItems"
          :key="item.id"
          class="inventory-row"
          :class="{ active: item.id === selectedItemId }"
          @click="chooseInventoryItem(item)"
        >
          <div class="row-main">
            <div class="row-heading">
              <h4>{{ item.material_name }}</h4>
              <span :class="['stock-chip', Number(item.quantity_on_hand) <= 5 ? 'danger' : 'safe']">
                {{ item.quantity_on_hand }} {{ item.unit || '件' }}
              </span>
            </div>

            <div class="row-meta">
              <span>规格：{{ item.specification || '未填' }}</span>
              <span>供应商：{{ item.supplier_name || '未填' }}</span>
              <span>区位：{{ item.location_name || '未填' }}</span>
              <span>项目：{{ item.project_name || '未填' }}</span>
            </div>
          </div>
        </article>

        <div v-if="loading" class="empty-state">正在加载库存数据...</div>
        <div v-else-if="!filteredItems.length" class="empty-state">没有匹配到库存项目。</div>
      </div>
    </section>

    <div class="page-stack">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">当前操作对象</p>
            <h3>{{ selectedItem?.material_name || '请选择一个库存项目' }}</h3>
          </div>
          <span class="section-meta">{{ pageLabel }}</span>
        </div>

        <div v-if="selectedItem" class="stat-grid">
          <article class="stat-card">
            <span>现有库存</span>
            <strong>{{ selectedItem.quantity_on_hand }}</strong>
            <small>{{ selectedItem.unit || '件' }}</small>
          </article>
          <article class="stat-card">
            <span>规格型号</span>
            <strong class="minor">{{ selectedItem.specification || '未填' }}</strong>
          </article>
          <article class="stat-card">
            <span>区位</span>
            <strong class="minor">{{ selectedItem.location_name || '未填' }}</strong>
          </article>
          <article class="stat-card">
            <span>最近入库</span>
            <strong class="minor">{{ selectedItem.last_receipt_at || '未记录' }}</strong>
          </article>
        </div>

        <div class="link-row">
          <RouterLink class="action-link secondary" :to="alternateRoute">{{ alternateLabel }}</RouterLink>
          <RouterLink class="action-link ghost" to="/overview">返回仓库总览</RouterLink>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">执行表单</p>
            <h3>{{ pageLabel }}</h3>
          </div>
          <span class="section-meta">单页聚焦单一动作</span>
        </div>

        <form class="form-stack" @submit.prevent="submitTransaction">
          <label class="field">
            <span>数量</span>
            <div class="quantity-editor">
              <button class="qty-button" type="button" @click="nudgeQuantity(-1)">-1</button>
              <input v-model.number="form.quantity" min="0.01" step="0.01" type="number" />
              <button class="qty-button" type="button" @click="nudgeQuantity(1)">+1</button>
            </div>
          </label>

          <div class="chip-row">
            <button v-for="qty in quickQuantities" :key="qty" class="quick-chip" type="button" @click="applyQuickQuantity(qty)">
              {{ qty }}
            </button>
          </div>

          <div class="toolbar-grid dual">
            <label class="field">
              <span>日期</span>
              <input v-model="form.occurred_on" type="date" />
            </label>

            <label class="field">
              <span>操作人</span>
              <input v-model="form.operator_name" type="text" placeholder="仓管员" />
            </label>
          </div>

          <label class="field">
            <span>单号 / 引用</span>
            <input v-model="form.reference_code" type="text" placeholder="例如 RK-20260517-01" />
          </label>

          <label class="field">
            <span>备注</span>
            <textarea v-model="form.notes" rows="4" placeholder="补充本次收发说明"></textarea>
          </label>

          <p v-if="issueBlockedReason" class="form-hint danger-text">{{ issueBlockedReason }}</p>

          <button class="primary-button" :class="{ issue: !isReceipt }" :disabled="submitDisabled" type="submit">
            {{ submitLabel }}
          </button>
        </form>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">最近流水</p>
            <h3>辅助核对</h3>
          </div>
          <span class="section-meta" v-if="selectedItem">物料 #{{ selectedItem.id }}</span>
        </div>

        <div class="stack-list">
          <article v-for="tx in itemTransactions" :key="tx.id" class="history-row">
            <div class="history-head">
              <strong :class="tx.transaction_type">{{ tx.transaction_type === 'receipt' ? '入库' : '出库' }}</strong>
              <span>{{ tx.occurred_on }}</span>
            </div>
            <div class="history-body">
              <span>数量：{{ tx.quantity }}</span>
              <span>操作人：{{ tx.operator_name || '未填' }}</span>
              <span>单号：{{ tx.reference_code || '未填' }}</span>
            </div>
            <p v-if="tx.notes" class="history-notes">{{ tx.notes }}</p>
          </article>

          <div v-if="historyLoading" class="empty-state">正在加载流水...</div>
          <div v-else-if="!itemTransactions.length" class="empty-state">当前物料还没有流水记录。</div>
        </div>
      </section>
    </div>
  </div>
</template>
