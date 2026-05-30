<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { postIssue, postReceipt } from '../services/api'
import type { InventoryItem, InventoryTransactionPayload } from '../types/inventory'

type TransactionMode = 'receipt' | 'issue'

const props = defineProps<{
  mode: TransactionMode
}>()

const route = useRoute()
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
const pageLabel = computed(() => (isReceipt.value ? '直接入库' : '直接出库'))
const pageDescription = computed(() =>
  isReceipt.value
    ? '适用于补货、退货、盘盈等非采购收货场景。'
    : '适用于领用、发放和其他直接出库场景。',
)
const submitLabel = computed(() => {
  if (submitting.value) {
    return '提交中...'
  }
  return isReceipt.value ? '确认直接入库' : '确认直接出库'
})
const referencePrefix = computed(() => (isReceipt.value ? 'RK-' : 'CK-'))
const currentSource = computed(() => (typeof route.query.source === 'string' ? route.query.source : 'overview'))
const receiptRoute = computed(() => ({
  path: '/receipt',
  query: selectedItemId.value ? { itemId: selectedItemId.value, source: currentSource.value } : { source: currentSource.value },
}))
const issueRoute = computed(() => ({
  path: '/issue',
  query: selectedItemId.value ? { itemId: selectedItemId.value, source: currentSource.value } : { source: currentSource.value },
}))
const selectedStockQuantity = computed(() => Number(selectedItem.value?.quantity_on_hand ?? 0))
const projectedStockQuantity = computed(() => {
  const current = selectedStockQuantity.value
  const delta = Number(form.value.quantity || 0)
  return Number((isReceipt.value ? current + delta : current - delta).toFixed(2))
})
const quantityError = computed(() => {
  const quantity = Number(form.value.quantity || 0)
  if (quantity <= 0) {
    return '数量必须大于 0。'
  }

  if (!isReceipt.value && selectedItem.value && quantity > selectedStockQuantity.value) {
    return `出库数量不能超过当前库存 ${selectedStockQuantity.value}。`
  }

  return ''
})
const occurredOnError = computed(() => (form.value.occurred_on ? '' : '请选择业务日期。'))
const issueBlockedReason = computed(() => {
  if (isReceipt.value || !selectedItem.value) {
    return ''
  }

  if (selectedStockQuantity.value <= 0) {
    return '当前物料库存为 0，不能执行出库。'
  }

  return quantityError.value
})
const submitDisabled = computed(
  () => submitting.value || !selectedItem.value || Boolean(quantityError.value) || Boolean(occurredOnError.value),
)

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

function syncRouteSelection() {
  const queryItemId = Number(route.query.itemId)
  if (!Number.isFinite(queryItemId) || queryItemId <= 0) {
    return
  }

  const matchedItem = inventoryItems.value.find((item) => item.id === queryItemId)
  if (matchedItem) {
    chooseInventoryItem(matchedItem)
  }
}

async function submitTransaction() {
  if (!selectedItemId.value) {
    ElMessage.warning('请先选择一个库存项目。')
    return
  }

  if (quantityError.value) {
    ElMessage.warning(quantityError.value)
    return
  }

  if (occurredOnError.value) {
    ElMessage.warning(occurredOnError.value)
    return
  }

  submitting.value = true
  form.value.item_id = selectedItemId.value

  try {
    if (isReceipt.value) {
      await postReceipt(form.value)
      ElMessage.success('直接入库已登记。')
    } else {
      await postIssue(form.value)
      ElMessage.success('直接出库已登记。')
    }

    await loadDashboard({ quiet: true })
    await loadTransactions(selectedItemId.value)
    resetActionFields()
    syncRouteSelection()
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

watch(
  () => route.query.itemId,
  () => {
    syncRouteSelection()
  },
)

watch(inventoryItems, () => {
  syncRouteSelection()
})

onMounted(async () => {
  form.value.reference_code = referencePrefix.value
  await loadDashboard()
  syncRouteSelection()
})
</script>

<template>
  <div class="content-grid operation-layout">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">作业对象</p>
          <h3>{{ pageLabel }}</h3>
        </div>
        <span class="section-meta">{{ filteredItems.length }} / {{ inventoryItems.length }}</span>
      </div>

      <div class="inline-summary-row">
        <span>{{ pageDescription }}</span>
        <span>当前对象 <strong>{{ selectedItem?.material_name || '未选择' }}</strong></span>
        <span>{{ isReceipt ? '入库后会累加库存' : '出库前会校验余量' }}</span>
      </div>

      <div class="toolbar-grid compact-toolbar">
        <label class="field">
          <span>搜索物料</span>
          <input v-model="searchKeyword" type="text" placeholder="按物料、规格、供应商、区位搜索" />
        </label>

        <button class="soft-button" :class="{ active: lowStockOnly }" type="button" @click="lowStockOnly = !lowStockOnly">
          {{ lowStockOnly ? '当前只看低库存' : '只看低库存' }}
        </button>
      </div>

      <div class="console-table desktop-only">
        <div class="console-table-scroll">
          <div class="console-table-header inventory-pick-table-grid">
            <span class="console-header-cell">物料</span>
            <span class="console-header-cell">规格</span>
            <span class="console-header-cell">单位</span>
            <span class="console-header-cell">供应商</span>
            <span class="console-header-cell">区位</span>
            <span class="console-header-cell">项目</span>
            <span class="console-header-cell align-right">库存</span>
            <span class="console-header-cell align-right">最近入库</span>
            <span class="console-header-cell">操作</span>
          </div>

          <article
            v-for="item in filteredItems"
            :key="item.id"
            class="console-table-row inventory-pick-table-grid interactive"
            role="button"
            tabindex="0"
            :class="{ active: item.id === selectedItemId }"
            @click="chooseInventoryItem(item)"
            @keydown.enter.prevent="chooseInventoryItem(item)"
            @keydown.space.prevent="chooseInventoryItem(item)"
          >
            <div class="console-cell">
              <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
            </div>
            <div class="console-cell muted console-clamp-2" :title="item.specification || '未填'">{{ item.specification || '未填' }}</div>
            <div class="console-cell muted console-nowrap" :title="item.unit || '件'">{{ item.unit || '件' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填'">{{ item.supplier_name || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.location_name || '未填'">{{ item.location_name || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.project_name || '未填'">{{ item.project_name || '未填' }}</div>
            <div class="console-cell align-right">
              <span :class="['console-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                {{ item.quantity_on_hand }} {{ item.unit || '件' }}
              </span>
            </div>
            <div class="console-cell muted console-nowrap align-right" :title="item.last_receipt_at || '未记录'">
              {{ item.last_receipt_at || '未记录' }}
            </div>
            <div class="console-row-actions" @click.stop>
              <button class="console-action primary" type="button" @click="chooseInventoryItem(item)">选择</button>
            </div>
          </article>
        </div>

        <div v-if="loading" class="console-empty">正在加载库存数据...</div>
        <div v-else-if="!filteredItems.length" class="console-empty">没有匹配到库存项目。</div>
      </div>

      <div class="mobile-only mobile-flow-stack">
        <div class="stack-list">
          <article
            v-for="item in filteredItems"
            :key="item.id"
            class="data-row clickable mobile-task-card"
            role="button"
            tabindex="0"
            :class="{ active: item.id === selectedItemId }"
            @click="chooseInventoryItem(item)"
            @keydown.enter.prevent="chooseInventoryItem(item)"
            @keydown.space.prevent="chooseInventoryItem(item)"
          >
            <div class="data-row-main">
              <div class="data-row-head">
                <strong>{{ item.material_name }}</strong>
                <span :class="['data-row-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                  {{ item.quantity_on_hand }} {{ item.unit || '件' }}
                </span>
              </div>
              <div class="data-row-meta">
                <span>规格：{{ item.specification || '未填' }}</span>
                <span>供应商：{{ item.supplier_name || '未填' }}</span>
                <span>区位：{{ item.location_name || '未填' }}</span>
                <span>项目：{{ item.project_name || '未填' }}</span>
                <span>最近入库：{{ item.last_receipt_at || '未记录' }}</span>
              </div>
            </div>

            <div class="data-row-actions">
              <button class="action-link" type="button" @click.stop="chooseInventoryItem(item)">选择</button>
            </div>
          </article>

          <div v-if="loading" class="empty-state">正在加载库存数据...</div>
          <div v-else-if="!filteredItems.length" class="empty-state">没有匹配到库存项目。</div>
        </div>
      </div>
    </section>

    <div class="page-stack">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">本次作业</p>
            <h3>{{ selectedItem?.material_name || '先选择一个库存项目' }}</h3>
          </div>
          <span class="section-meta">{{ pageLabel }}</span>
        </div>

        <div class="segment-switch">
          <RouterLink class="segment-chip" :class="{ active: isReceipt }" :to="receiptRoute">直接入库</RouterLink>
          <RouterLink class="segment-chip" :class="{ active: !isReceipt }" :to="issueRoute">直接出库</RouterLink>
        </div>

        <form class="form-stack" @submit.prevent="submitTransaction">
          <div class="receipt-summary emphasis-summary">
            <p>物料：{{ selectedItem?.material_name || '未选择' }}</p>
            <p>规格：{{ selectedItem?.specification || '未填规格' }}</p>
            <p>区位：{{ selectedItem?.location_name || '未填区位' }}</p>
            <p>当前库存：{{ selectedItem?.quantity_on_hand || '--' }} {{ selectedItem?.unit || '件' }}</p>
            <p>本次变动后：{{ selectedItem ? projectedStockQuantity : '--' }} {{ selectedItem?.unit || '件' }}</p>
          </div>

          <label class="field">
            <span>数量</span>
            <div class="quantity-editor">
              <button class="qty-button" type="button" @click="nudgeQuantity(-1)">-1</button>
              <input v-model.number="form.quantity" min="0.01" step="0.01" type="number" inputmode="decimal" />
              <button class="qty-button" type="button" @click="nudgeQuantity(1)">+1</button>
            </div>
            <small v-if="quantityError" class="field-hint danger">{{ quantityError }}</small>
            <small v-else class="field-hint">{{ isReceipt ? '数量会累加到当前库存。' : '提交后会从当前库存中扣减。' }}</small>
          </label>

          <div class="chip-row">
            <button v-for="qty in quickQuantities" :key="qty" class="quick-chip" type="button" @click="applyQuickQuantity(qty)">
              {{ qty }}
            </button>
          </div>

          <div class="toolbar-grid dual">
            <label class="field">
              <span>业务日期</span>
              <input v-model="form.occurred_on" type="date" />
              <small v-if="occurredOnError" class="field-hint danger">{{ occurredOnError }}</small>
            </label>

            <label class="field">
              <span>操作人</span>
              <input v-model="form.operator_name" type="text" placeholder="仓管员" />
              <small class="field-hint">会保留本次会话的填写习惯。</small>
            </label>
          </div>

          <label class="field">
            <span>单号 / 引用</span>
            <input v-model="form.reference_code" type="text" :placeholder="`例如 ${referencePrefix}20260530-01`" />
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
            <p class="section-kicker">辅助核对</p>
            <h3>{{ selectedItem ? '最近流水' : '还没有选择物料' }}</h3>
          </div>
          <span class="section-meta">{{ selectedItem ? `物料 #${selectedItem.id}` : '请先选择对象' }}</span>
        </div>

        <div class="link-row">
          <RouterLink class="action-link ghost" to="/overview">返回库存台账</RouterLink>
        </div>

        <div class="console-table desktop-only">
          <div class="console-table-scroll">
            <div class="console-table-header history-table-grid">
              <span class="console-header-cell">类型</span>
              <span class="console-header-cell align-right">时间</span>
              <span class="console-header-cell align-right">数量</span>
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
              <div class="console-cell muted console-nowrap align-right" :title="tx.occurred_on">{{ tx.occurred_on }}</div>
              <div class="console-cell align-right">
                <strong>{{ tx.quantity }} {{ selectedItem?.unit || '件' }}</strong>
              </div>
              <div class="console-cell muted console-clamp-2" :title="tx.operator_name || '未填'">{{ tx.operator_name || '未填' }}</div>
              <div class="console-cell muted console-nowrap" :title="tx.reference_code || '未填'">{{ tx.reference_code || '未填' }}</div>
              <div class="console-cell muted console-clamp-2" :title="tx.notes || '无'">{{ tx.notes || '无' }}</div>
            </article>
          </div>

          <div v-if="historyLoading" class="console-empty">正在加载流水...</div>
          <div v-else-if="!selectedItem" class="console-empty">请先从左侧列表选择一个库存项目。</div>
          <div v-else-if="!itemTransactions.length" class="console-empty">当前物料还没有流水记录。</div>
        </div>

        <div class="mobile-only mobile-flow-stack">
          <div class="stack-list">
            <article v-for="tx in itemTransactions" :key="tx.id" class="data-row mobile-task-card history-mobile-card">
              <div class="data-row-main">
                <div class="data-row-head">
                  <span :class="['data-row-badge', tx.transaction_type === 'receipt' ? 'ok' : 'warn']">
                    {{ tx.transaction_type === 'receipt' ? '入库' : '出库' }}
                  </span>
                  <strong>{{ tx.quantity }} {{ selectedItem?.unit || '件' }}</strong>
                </div>
                <div class="data-row-meta">
                  <span>时间：{{ tx.occurred_on }}</span>
                  <span>操作人：{{ tx.operator_name || '未填' }}</span>
                  <span>单号：{{ tx.reference_code || '未填' }}</span>
                  <span>备注：{{ tx.notes || '无' }}</span>
                </div>
              </div>
            </article>

            <div v-if="historyLoading" class="empty-state">正在加载流水...</div>
            <div v-else-if="!selectedItem" class="empty-state">请先从左侧列表选择一个库存项目。</div>
            <div v-else-if="!itemTransactions.length" class="empty-state">当前物料还没有流水记录。</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
