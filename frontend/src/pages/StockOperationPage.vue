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
    ? '登记入库信息。'
    : '登记出库信息。'
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

      <div class="console-table">
        <div class="console-table-scroll">
          <div class="console-table-header inventory-pick-table-grid">
            <span class="console-header-cell">物料</span>
            <span class="console-header-cell">规格</span>
            <span class="console-header-cell">供应商</span>
            <span class="console-header-cell">区位</span>
            <span class="console-header-cell">项目</span>
            <span class="console-header-cell">库存</span>
            <span class="console-header-cell">最近入库</span>
            <span class="console-header-cell">操作</span>
          </div>

          <article
            v-for="item in filteredItems"
            :key="item.id"
            class="console-table-row inventory-pick-table-grid interactive"
            :class="{ active: item.id === selectedItemId }"
            @click="chooseInventoryItem(item)"
          >
            <div class="console-cell">
              <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
              <span class="console-subtext">#{{ item.id }}</span>
            </div>
            <div class="console-cell muted console-clamp-2" :title="item.specification || '未填'">{{ item.specification || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填'">{{ item.supplier_name || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.location_name || '未填'">{{ item.location_name || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.project_name || '未填'">{{ item.project_name || '未填' }}</div>
            <div class="console-cell">
              <span :class="['console-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                {{ item.quantity_on_hand }} {{ item.unit || '件' }}
              </span>
            </div>
            <div class="console-cell muted console-nowrap" :title="item.last_receipt_at || '未记录'">{{ item.last_receipt_at || '未记录' }}</div>
            <div class="console-row-actions" @click.stop>
              <button class="console-action primary" type="button" @click="chooseInventoryItem(item)">选择</button>
            </div>
          </article>
        </div>

        <div v-if="loading" class="console-empty">正在加载库存数据...</div>
        <div v-else-if="!filteredItems.length" class="console-empty">没有匹配到库存项目。</div>
      </div>
    </section>

    <div class="page-stack">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">执行表单</p>
            <h3>{{ pageLabel }}</h3>
          </div>
          <span class="section-meta">表单</span>
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
            <p class="section-kicker">页面切换</p>
            <h3>{{ selectedItem?.material_name || '请选择一个库存项目' }}</h3>
          </div>
          <span class="section-meta">{{ pageLabel }}</span>
        </div>

        <div class="link-row">
          <RouterLink class="action-link secondary" :to="alternateRoute">{{ alternateLabel }}</RouterLink>
          <RouterLink class="action-link ghost" to="/overview">返回仓库总览</RouterLink>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">最近流水</p>
            <h3>辅助核对</h3>
          </div>
          <span class="section-meta" v-if="selectedItem">物料 #{{ selectedItem.id }}</span>
        </div>

        <div class="console-table">
          <div class="console-table-scroll">
            <div class="console-table-header history-table-grid">
              <span class="console-header-cell">类型</span>
              <span class="console-header-cell">时间</span>
              <span class="console-header-cell">数量</span>
              <span class="console-header-cell">操作人</span>
              <span class="console-header-cell">单号</span>
              <span class="console-header-cell">备注</span>
            </div>

            <article v-for="tx in itemTransactions" :key="tx.id" class="console-table-row history-table-grid">
              <div class="console-cell">
                <span :class="['console-badge', tx.transaction_type === 'receipt' ? 'ok' : 'warn']">
                  {{ tx.transaction_type === 'receipt' ? '入库' : '出库' }}
                </span>
              </div>
              <div class="console-cell muted console-nowrap" :title="tx.occurred_on">{{ tx.occurred_on }}</div>
              <div class="console-cell">
                <strong>{{ tx.quantity }}</strong>
              </div>
              <div class="console-cell muted console-clamp-2" :title="tx.operator_name || '未填'">{{ tx.operator_name || '未填' }}</div>
              <div class="console-cell muted console-nowrap" :title="tx.reference_code || '未填'">{{ tx.reference_code || '未填' }}</div>
              <div class="console-cell muted console-clamp-2" :title="tx.notes || '无'">{{ tx.notes || '无' }}</div>
            </article>
          </div>

          <div v-if="historyLoading" class="console-empty">正在加载流水...</div>
          <div v-else-if="!itemTransactions.length" class="console-empty">当前物料还没有流水记录。</div>
        </div>
      </section>
    </div>
  </div>
</template>
