<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { deleteInventoryItems } from '../services/api'
import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'

const { dashboard, historyLoading, inventoryItems, itemTransactions, loading, loadDashboard, selectItem, selectedItem, selectedItemId } =
  useInventoryWorkspace()

const searchKeyword = ref('')
const lowStockOnly = ref(false)
const deleting = ref(false)
const selectedDeleteIds = ref<number[]>([])

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

const allFilteredIds = computed(() => filteredItems.value.map((item) => item.id))
const selectedFilteredIds = computed(() =>
  allFilteredIds.value.filter((itemId) => selectedDeleteIds.value.includes(itemId)),
)
const allFilteredSelected = computed(
  () => allFilteredIds.value.length > 0 && selectedFilteredIds.value.length === allFilteredIds.value.length,
)
const hasSelectedDeleteItems = computed(() => selectedDeleteIds.value.length > 0)

function toggleItemSelection(itemId: number) {
  if (selectedDeleteIds.value.includes(itemId)) {
    selectedDeleteIds.value = selectedDeleteIds.value.filter((id) => id !== itemId)
    return
  }

  selectedDeleteIds.value = [...selectedDeleteIds.value, itemId]
}

function toggleSelectAllFiltered() {
  if (allFilteredSelected.value) {
    selectedDeleteIds.value = selectedDeleteIds.value.filter((id) => !allFilteredIds.value.includes(id))
    return
  }

  selectedDeleteIds.value = [...new Set([...selectedDeleteIds.value, ...allFilteredIds.value])]
}

async function handleBulkDelete() {
  if (!selectedDeleteIds.value.length) {
    ElMessage.warning('请先勾选要删除的库存项目。')
    return
  }

  try {
    await ElMessageBox.confirm(
      `将删除 ${selectedDeleteIds.value.length} 个库存项目，并一并清除对应库存流水。此操作仅建议在开发阶段使用。`,
      '确认删除库存',
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
    const response = await deleteInventoryItems(selectedDeleteIds.value)
    selectedDeleteIds.value = selectedDeleteIds.value.filter((id) => !response.deleted_item_ids.includes(id))
    await loadDashboard()
    ElMessage.success(`已删除 ${response.deleted_count} 个库存项目。`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '删除库存失败'
    ElMessage.error(message)
  } finally {
    deleting.value = false
  }
}

watch(inventoryItems, (items) => {
  const currentIds = new Set(items.map((item) => item.id))
  selectedDeleteIds.value = selectedDeleteIds.value.filter((id) => currentIds.has(id))
})

onMounted(async () => {
  await loadDashboard()
})
</script>

<template>
  <div class="page-stack">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">全局视图</p>
          <h3>库存态势一屏可见</h3>
        </div>
        <span class="section-meta">{{ dashboard ? `${dashboard.summary.total_items} 项物料` : '加载中' }}</span>
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
        <article class="metric-card danger">
          <span>低库存</span>
          <strong>{{ dashboard?.summary.low_stock_items ?? '--' }}</strong>
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
            <p class="section-kicker">库存列表</p>
            <h3>快速定位物料</h3>
          </div>
          <span class="section-meta">{{ filteredItems.length }} / {{ inventoryItems.length }}</span>
        </div>

        <div class="toolbar-grid">
          <label class="field">
            <span>搜索</span>
            <input v-model="searchKeyword" type="text" placeholder="按物料、规格、供应商、区位搜索" />
          </label>

          <button class="soft-button" :class="{ active: lowStockOnly }" type="button" @click="lowStockOnly = !lowStockOnly">
            {{ lowStockOnly ? '只看低库存中' : '切到低库存' }}
          </button>
        </div>

        <div class="selection-toolbar">
          <label class="checkbox-chip">
            <input :checked="allFilteredSelected" type="checkbox" @change="toggleSelectAllFiltered" />
            <span>全选当前筛选结果</span>
          </label>

          <div class="selection-actions">
            <span>{{ selectedDeleteIds.length }} 项待删除</span>
            <button class="danger-button" :disabled="deleting || !hasSelectedDeleteItems" type="button" @click="handleBulkDelete">
              {{ deleting ? '删除中...' : '删除勾选库存' }}
            </button>
          </div>
        </div>

        <div class="inventory-list">
          <article
            v-for="item in filteredItems"
            :key="item.id"
            class="inventory-row"
            :class="{ active: item.id === selectedItemId }"
            @click="selectItem(item)"
          >
            <label class="row-checkbox" @click.stop>
              <input
                :checked="selectedDeleteIds.includes(item.id)"
                type="checkbox"
                @change="toggleItemSelection(item.id)"
              />
            </label>

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
              <p class="section-kicker">当前物料</p>
              <h3>{{ selectedItem?.material_name || '请选择一个库存项目' }}</h3>
            </div>
            <span class="section-meta">总览详情</span>
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
              <span>最近出库</span>
              <strong class="minor">{{ selectedItem.last_issue_at || '未记录' }}</strong>
            </article>
          </div>

          <div class="link-row">
            <RouterLink class="action-link ghost" to="/inventory-import">去做库存导入</RouterLink>
            <RouterLink class="action-link ghost" to="/inventory-export">去做库存导出</RouterLink>
            <RouterLink class="action-link" to="/receipt">去做入库</RouterLink>
            <RouterLink class="action-link secondary" to="/issue">去做出库</RouterLink>
          </div>
        </section>

        <section class="page-section">
          <div class="section-heading">
            <div>
              <p class="section-kicker">流水</p>
              <h3>最近 12 条记录</h3>
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
  </div>
</template>
