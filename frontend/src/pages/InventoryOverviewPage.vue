<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useAuth } from '../composables/useAuth'
import { useFinishedInventoryWorkspace } from '../composables/useFinishedInventoryWorkspace'
import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { deleteInventoryItems } from '../services/api'
import type { FinishedInventoryItem, InventoryViewKind } from '../types/inventory'

const route = useRoute()
const { isAuthenticated } = useAuth()
const {
  dashboard,
  historyLoading,
  inventoryItems,
  itemTransactions,
  loading,
  loadDashboard,
  selectItem,
  selectedItem,
  selectedItemId,
} = useInventoryWorkspace()
const {
  dashboard: finishedDashboard,
  historyLoading: finishedHistoryLoading,
  inventoryItems: finishedItems,
  itemTransactions: finishedTransactions,
  loading: finishedLoading,
  loadDashboard: loadFinishedDashboard,
  selectItem: selectFinishedItem,
  selectedItem: selectedFinishedItem,
  selectedItemId: selectedFinishedItemId,
} = useFinishedInventoryWorkspace()

const searchKeyword = ref('')
const lowStockOnly = ref(false)
const deleting = ref(false)
const selectedDeleteIds = ref<number[]>([])
const activeKind = computed<InventoryViewKind>(() => (route.query.kind === 'finished' ? 'finished' : 'raw'))
const isFinishedView = computed(() => activeKind.value === 'finished')

const filteredItems = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()

  return inventoryItems.value.filter((item) => {
    const matchesKeyword =
      !keyword ||
      (item.item_code ?? '').toLowerCase().includes(keyword) ||
      item.material_name.toLowerCase().includes(keyword) ||
      (item.specification ?? '').toLowerCase().includes(keyword) ||
      (isAuthenticated.value && (item.supplier_name ?? '').toLowerCase().includes(keyword)) ||
      (isAuthenticated.value && (item.location_name ?? '').toLowerCase().includes(keyword))

    const matchesLowStock = !lowStockOnly.value || Number(item.quantity_on_hand) <= 5

    return matchesKeyword && matchesLowStock
  })
})

const filteredFinishedItems = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()

  return finishedItems.value.filter((item) => {
    const matchesKeyword =
      !keyword ||
      item.material_name.toLowerCase().includes(keyword) ||
      (item.specification ?? '').toLowerCase().includes(keyword) ||
      (item.work_order_no ?? '').toLowerCase().includes(keyword) ||
      (item.location_name ?? '').toLowerCase().includes(keyword) ||
      (item.project_code ?? '').toLowerCase().includes(keyword) ||
      (item.producer_name ?? '').toLowerCase().includes(keyword) ||
      (item.customer_name ?? '').toLowerCase().includes(keyword) ||
      (item.notes ?? '').toLowerCase().includes(keyword)

    const matchesLowStock = !lowStockOnly.value || Number(item.quantity_on_hand) <= 5

    return matchesKeyword && matchesLowStock
  })
})

const searchPlaceholder = computed(() =>
  !isAuthenticated.value
    ? '按物料名称或规格搜索'
    : isFinishedView.value
      ? '按物料、规格、工单号、库位、项目号、客户名称搜索'
      : '按编号、物料、规格、供应商、区位搜索',
)

const allFilteredIds = computed(() => filteredItems.value.map((item) => item.id))
const selectedFilteredIds = computed(() =>
  allFilteredIds.value.filter((itemId) => selectedDeleteIds.value.includes(itemId)),
)
const allFilteredSelected = computed(
  () => allFilteredIds.value.length > 0 && selectedFilteredIds.value.length === allFilteredIds.value.length,
)
const hasSelectedDeleteItems = computed(() => selectedDeleteIds.value.length > 0)
const routeItemId = computed(() => {
  const queryId = Number(route.query.itemId)
  return Number.isFinite(queryId) && queryId > 0 ? queryId : null
})

const currentSummary = computed(() =>
  isFinishedView.value
    ? finishedDashboard.value?.summary ?? { total_items: 0, total_stock_quantity: '0', low_stock_items: 0 }
    : dashboard.value?.summary ?? { total_items: 0, total_stock_quantity: '0', low_stock_items: 0, pending_purchase_orders: 0 },
)
const selectedOverviewName = computed(() =>
  isFinishedView.value ? selectedFinishedItem.value?.material_name || '先选择一个成品' : selectedItem.value?.material_name || '先选择一个物料',
)
const selectedOverviewNextStep = computed(() => {
  if (isFinishedView.value) {
    return selectedFinishedItem.value ? '查看派生流水并核对收发记录' : '先在下方成品台账中锁定对象'
  }

  return selectedItem.value ? (isAuthenticated.value ? '查看流水或发起入库 / 出库' : '可继续筛选并核对库存') : '先在下方台账中锁定对象'
})
const currentFilteredCount = computed(() => (isFinishedView.value ? filteredFinishedItems.value.length : filteredItems.value.length))
const currentTotalCount = computed(() => (isFinishedView.value ? finishedItems.value.length : inventoryItems.value.length))

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
      `将删除 ${selectedDeleteIds.value.length} 个库存项目，并一并清除对应库存流水、采购收货关联和已收货数量回滚。此操作仅建议在开发阶段使用。`,
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

async function scrollItemIntoView(itemId: number) {
  await nextTick()
  document
    .querySelector<HTMLElement>(`[data-item-id="${itemId}"]`)
    ?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

async function syncRouteSelection() {
  if (isFinishedView.value || !routeItemId.value) {
    return
  }

  const matchedItem = inventoryItems.value.find((item) => item.id === routeItemId.value)
  if (!matchedItem) {
    return
  }

  if (selectedItemId.value !== matchedItem.id) {
    selectItem(matchedItem)
  }

  await scrollItemIntoView(matchedItem.id)
}

function selectFinishedInventoryItem(item: FinishedInventoryItem) {
  selectFinishedItem(item)
}

watch(inventoryItems, (items) => {
  const currentIds = new Set(items.map((item) => item.id))
  selectedDeleteIds.value = selectedDeleteIds.value.filter((id) => currentIds.has(id))
  void syncRouteSelection()
})

watch(
  () => route.query.itemId,
  () => {
    void syncRouteSelection()
  },
)

watch(
  activeKind,
  async (kind) => {
    if (kind === 'finished') {
      if (!finishedDashboard.value) {
        await loadFinishedDashboard()
      }
      return
    }

    if (!dashboard.value) {
      await loadDashboard()
    }
    await syncRouteSelection()
  },
  { immediate: false },
)

onMounted(async () => {
  if (isFinishedView.value) {
    await loadFinishedDashboard()
    return
  }

  await loadDashboard()
  await syncRouteSelection()
})
</script>

<template>
  <div class="page-stack">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">{{ isFinishedView ? '成品态势' : '库存态势' }}</p>
          <h3>{{ isFinishedView ? '先看成品全局，再定位单个对象' : '先看全局，再定位单个物料' }}</h3>
        </div>
        <span class="section-meta">{{ currentSummary ? `${currentSummary.total_items} 项${isFinishedView ? '成品' : '物料'}` : '加载中' }}</span>
      </div>

      <div class="metric-grid compact">
        <article class="metric-card">
          <span>{{ isFinishedView ? '成品项目' : '库存项目' }}</span>
          <strong>{{ currentSummary.total_items ?? '--' }}</strong>
        </article>
        <article class="metric-card">
          <span>{{ isFinishedView ? '成品总量' : '库存总量' }}</span>
          <strong>{{ currentSummary.total_stock_quantity ?? '--' }}</strong>
        </article>
        <article class="metric-card danger">
          <span>低库存</span>
          <strong>{{ currentSummary.low_stock_items ?? '--' }}</strong>
        </article>
        <article v-if="isFinishedView" class="metric-card accent">
          <span>当前口径</span>
          <strong>成品只读</strong>
        </article>
        <article v-else-if="isAuthenticated" class="metric-card accent">
          <span>待处理采购</span>
          <strong>{{ dashboard?.summary.pending_purchase_orders ?? '--' }}</strong>
        </article>
        <article v-else class="metric-card accent">
          <span>当前权限</span>
          <strong>游客查询</strong>
        </article>
      </div>

      <div class="status-strip workflow-strip">
        <div>
          <span>当前筛选</span>
          <strong>{{ lowStockOnly ? '仅低库存' : '全部库存' }}</strong>
        </div>
        <div>
          <span>当前对象</span>
          <strong>{{ selectedOverviewName }}</strong>
        </div>
        <div>
          <span>下一步</span>
          <strong>{{ selectedOverviewNextStep }}</strong>
        </div>
      </div>
    </section>

    <section class="page-section sticky-head-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">{{ isFinishedView ? '成品台账' : '库存台账' }}</p>
          <h3>{{ isFinishedView ? '搜索、筛选并核对成品库存' : '搜索、筛选并选择作业对象' }}</h3>
        </div>
        <span class="section-meta">{{ currentFilteredCount }} / {{ currentTotalCount }}</span>
      </div>

      <div class="toolbar-grid">
        <label class="field">
          <span>搜索</span>
          <input v-model="searchKeyword" type="text" :placeholder="searchPlaceholder" />
        </label>

        <button class="soft-button" :class="{ active: lowStockOnly }" type="button" @click="lowStockOnly = !lowStockOnly">
          {{ lowStockOnly ? '当前只看低库存' : '只看低库存' }}
        </button>
      </div>

      <div v-if="isFinishedView && isAuthenticated" class="selection-toolbar business-toolbar">
        <div class="selection-status">
          <span>当前查看对象</span>
          <strong>{{ selectedFinishedItem?.material_name || '先从下方成品台账选择对象' }}</strong>
          <small>
            {{
              selectedFinishedItem
                ? `库存 ${selectedFinishedItem.quantity_on_hand} ${selectedFinishedItem.unit || '件'} / 库位 ${selectedFinishedItem.location_name || '未填'} / 客户 ${selectedFinishedItem.customer_name || '未填'}`
                : '当前成品口径为只读模式，可继续搜索、筛选并查看派生流水。'
            }}
          </small>
        </div>

        <div class="selection-actions">
          <span class="action-link ghost disabled">成品视图暂不开放直接入库</span>
          <span class="action-link secondary disabled">成品视图暂不开放直接出库</span>
        </div>
      </div>

      <div v-else-if="isFinishedView" class="selection-toolbar business-toolbar">
        <div class="selection-status">
          <span>游客权限</span>
          <strong>{{ selectedFinishedItem?.material_name || '当前开放成品台账只读查询' }}</strong>
          <small>
            {{
              selectedFinishedItem
                ? `规格 ${selectedFinishedItem.specification || '未填'} / 库存 ${selectedFinishedItem.quantity_on_hand} ${selectedFinishedItem.unit || '件'}`
                : '游客模式下仅展示物料名称、规格和库存，可继续筛选并核对派生流水。'
            }}
          </small>
        </div>

        <div class="selection-actions">
          <span class="action-link ghost disabled">游客模式仅保留只读查询</span>
        </div>
      </div>

      <div v-else-if="isAuthenticated" class="selection-toolbar business-toolbar">
        <div class="selection-status">
          <span>当前作业对象</span>
          <strong>{{ selectedItem?.material_name || '先从下方台账选择物料' }}</strong>
          <small>
            {{
              selectedItem
                ? `库存 ${selectedItem.quantity_on_hand} ${selectedItem.unit || '件'} / 供应商 ${selectedItem.supplier_name || '未填'} / 区位 ${selectedItem.location_name || '未填'}`
                : '选中后可直接发起入库或出库'
            }}
          </small>
        </div>

        <div class="selection-actions">
          <RouterLink v-if="selectedItem" class="action-link" :to="{ path: '/receipt', query: { itemId: selectedItem.id, source: 'overview' } }">
            直接入库
          </RouterLink>
          <span v-else class="action-link disabled">先选物料再入库</span>
          <RouterLink v-if="selectedItem" class="action-link secondary" :to="{ path: '/issue', query: { itemId: selectedItem.id, source: 'overview' } }">
            直接出库
          </RouterLink>
          <span v-else class="action-link secondary disabled">先选物料再出库</span>
        </div>
      </div>

      <div v-else class="selection-toolbar business-toolbar">
        <div class="selection-status">
          <span>游客权限</span>
          <strong>{{ isFinishedView ? '当前开放成品台账与派生流水只读查询' : '当前仅开放库存台账基础查询' }}</strong>
          <small>
            {{
              isFinishedView
                ? '成品视图当前为只读模式，登录不会解锁额外作业入口。'
                : '登录后可查看金额、供应商、流水，并执行入库、出库、导入导出等操作。'
            }}
          </small>
        </div>

        <div class="selection-actions">
          <RouterLink v-if="!isFinishedView" class="action-link primary" to="/login">管理员登录</RouterLink>
          <span v-else class="action-link ghost disabled">成品视图当前仅供核对</span>
        </div>
      </div>

      <div v-if="isFinishedView" class="console-table sticky-head-table desktop-only ledger-window">
        <div class="console-table-scroll">
          <table class="console-data-table dense-table finished-overview-data-table">
            <colgroup v-if="isAuthenticated">
              <col style="width: 260px" />
              <col style="width: 240px" />
              <col style="width: 160px" />
              <col style="width: 160px" />
              <col style="width: 160px" />
              <col style="width: 200px" />
              <col style="width: 200px" />
              <col style="width: 120px" />
              <col style="width: 130px" />
              <col style="width: 130px" />
            </colgroup>
            <colgroup v-else>
              <col style="width: 300px" />
              <col style="width: 260px" />
              <col style="width: 140px" />
            </colgroup>
            <thead>
              <tr v-if="isAuthenticated">
                <th>物料名称</th>
                <th>规格型号</th>
                <th>工单号</th>
                <th>库位</th>
                <th>项目号</th>
                <th>生产抬头或供应商</th>
                <th>客户名称</th>
                <th class="align-right">库存</th>
                <th class="align-right">最近入库</th>
                <th class="align-right">最近出库</th>
              </tr>
              <tr v-else>
                <th>物料名称</th>
                <th>规格型号</th>
                <th class="align-right">库存</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredFinishedItems"
                :key="item.row_id"
                :data-finished-row-id="item.row_id"
                class="console-data-row interactive"
                :class="{ active: item.row_id === selectedFinishedItemId }"
                @click="selectFinishedInventoryItem(item)"
              >
                <td class="console-data-cell">
                  <div class="console-cell">
                    <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
                    <small v-if="isAuthenticated" class="console-subline">Excel 行 #{{ item.row_id }}</small>
                  </div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.work_order_no || '未填工单号'">{{ item.work_order_no || '未填工单号' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.location_name || '未填库位'">{{ item.location_name || '未填库位' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.project_code || '未填项目号'">{{ item.project_code || '未填项目号' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.producer_name || '未填生产抬头或供应商'">{{ item.producer_name || '未填生产抬头或供应商' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.customer_name || '未填客户名称'">{{ item.customer_name || '未填客户名称' }}</div>
                </td>
                <td class="console-data-cell align-right v-middle">
                  <div class="console-cell">
                    <span :class="['console-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                      {{ item.quantity_on_hand }} {{ item.unit || '件' }}
                    </span>
                  </div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell align-right v-middle">
                  <div class="console-cell muted console-nowrap align-right" :title="item.last_receipt_at || '未记录'">{{ item.last_receipt_at || '未记录' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell align-right v-middle">
                  <div class="console-cell muted console-nowrap align-right" :title="item.last_issue_at || '未记录'">{{ item.last_issue_at || '未记录' }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="finishedLoading" class="console-empty">正在加载成品库存数据...</div>
        <div v-else-if="!filteredFinishedItems.length" class="console-empty">没有匹配到成品库存项目。</div>
      </div>

      <div v-else class="console-table sticky-head-table desktop-only ledger-window">
        <div class="console-table-scroll">
          <table class="console-data-table dense-table overview-data-table">
            <colgroup v-if="isAuthenticated">
              <col style="width: 56px" />
              <col style="width: 230px" />
              <col style="width: 160px" />
              <col style="width: 180px" />
              <col style="width: 180px" />
              <col style="width: 140px" />
              <col style="width: 180px" />
              <col style="width: 130px" />
              <col style="width: 120px" />
              <col style="width: 120px" />
              <col style="width: 130px" />
              <col style="width: 130px" />
            </colgroup>
            <colgroup v-else>
              <col style="width: 280px" />
              <col style="width: 260px" />
              <col style="width: 140px" />
            </colgroup>
            <thead>
              <tr v-if="isAuthenticated">
                <th class="console-data-head center">选中</th>
                <th>物料名称</th>
                <th>物品编号</th>
                <th>规格</th>
                <th>供应商</th>
                <th>区位</th>
                <th>项目</th>
                <th>申请人</th>
                <th class="align-right">库存</th>
                <th class="align-right">金额</th>
                <th class="align-right">最近入库</th>
                <th class="align-right">最近出库</th>
              </tr>
              <tr v-else>
                <th>物料名称</th>
                <th>规格</th>
                <th class="align-right">库存</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredItems"
                :key="item.id"
                :data-item-id="item.id"
                class="console-data-row interactive"
                :class="{ active: item.id === selectedItemId }"
                @click="selectItem(item)"
              >
                <td v-if="isAuthenticated" class="console-data-cell center">
                  <label class="console-checkbox" @click.stop>
                    <input
                      :checked="selectedDeleteIds.includes(item.id)"
                      type="checkbox"
                      @change="toggleItemSelection(item.id)"
                    />
                  </label>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell">
                    <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
                    <small class="console-subline">#{{ item.id }}</small>
                  </div>
                </td>
                <td class="console-data-cell">
                  <div v-if="isAuthenticated" class="console-cell muted console-clamp-2" :title="item.item_code || '未填编号'">
                    {{ item.item_code || '未填编号' }}
                  </div>
                  <div v-else class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">
                    {{ item.specification || '未填规格' }}
                  </div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填供应商'">{{ item.supplier_name || '未填供应商' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.location_name || '未填区位'">{{ item.location_name || '未填区位' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.project_name || '未填项目'">{{ item.project_name || '未填项目' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.requester || '未填申请人'">{{ item.requester || '未填申请人' }}</div>
                </td>
                <td class="console-data-cell align-right v-middle">
                  <div class="console-cell">
                    <span :class="['console-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                      {{ item.quantity_on_hand }} {{ item.unit || '件' }}
                    </span>
                  </div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell align-right v-middle">
                  <div class="console-cell muted console-nowrap align-right" :title="formatCurrency(item.total_amount)">{{ formatCurrency(item.total_amount) }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell align-right v-middle">
                  <div class="console-cell muted console-nowrap align-right" :title="item.last_receipt_at || '未记录'">{{ item.last_receipt_at || '未记录' }}</div>
                </td>
                <td v-if="isAuthenticated" class="console-data-cell align-right v-middle">
                  <div class="console-cell muted console-nowrap align-right" :title="item.last_issue_at || '未记录'">{{ item.last_issue_at || '未记录' }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="loading" class="console-empty">正在加载库存数据...</div>
        <div v-else-if="!filteredItems.length" class="console-empty">没有匹配到库存项目。</div>
      </div>

      <div class="mobile-only mobile-flow-stack">
        <div class="stack-list">
          <article
            v-if="isFinishedView"
            v-for="item in filteredFinishedItems"
            :key="item.row_id"
            class="data-row clickable triplet mobile-task-card"
            :class="{ active: item.row_id === selectedFinishedItemId }"
            role="button"
            tabindex="0"
            @click="selectFinishedInventoryItem(item)"
            @keydown.enter.prevent="selectFinishedInventoryItem(item)"
            @keydown.space.prevent="selectFinishedInventoryItem(item)"
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
                <template v-if="isAuthenticated">
                  <span>工单号：{{ item.work_order_no || '未填' }}</span>
                  <span>库位：{{ item.location_name || '未填' }}</span>
                  <span>项目号：{{ item.project_code || '未填' }}</span>
                  <span>生产抬头或供应商：{{ item.producer_name || '未填' }}</span>
                  <span>客户名称：{{ item.customer_name || '未填' }}</span>
                  <span>最近入库：{{ item.last_receipt_at || '未记录' }}</span>
                  <span>最近出库：{{ item.last_issue_at || '未记录' }}</span>
                </template>
              </div>
            </div>
          </article>

          <article
            v-else
            v-for="item in filteredItems"
            :key="item.id"
            :data-item-id="item.id"
            class="data-row clickable triplet mobile-task-card"
            :class="{ active: item.id === selectedItemId }"
            role="button"
            tabindex="0"
            @click="selectItem(item)"
            @keydown.enter.prevent="selectItem(item)"
            @keydown.space.prevent="selectItem(item)"
          >
            <label v-if="isAuthenticated" class="checkbox-chip mobile-select-chip" @click.stop>
              <input
                :checked="selectedDeleteIds.includes(item.id)"
                type="checkbox"
                @change="toggleItemSelection(item.id)"
              />
              <span>勾选清理</span>
            </label>

            <div class="data-row-main">
              <div class="data-row-head">
                <strong>{{ item.material_name }}</strong>
                <span :class="['data-row-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                  {{ item.quantity_on_hand }} {{ item.unit || '件' }}
                </span>
              </div>
              <div class="data-row-meta">
                <span>规格：{{ item.specification || '未填' }}</span>
                <span v-if="isAuthenticated">供应商：{{ item.supplier_name || '未填' }}</span>
                <span v-if="isAuthenticated">区位：{{ item.location_name || '未填' }}</span>
                <span v-if="isAuthenticated">金额：{{ formatCurrency(item.total_amount) }}</span>
                <span v-if="isAuthenticated">最近入库：{{ item.last_receipt_at || '未记录' }}</span>
                <span v-if="isAuthenticated">最近出库：{{ item.last_issue_at || '未记录' }}</span>
              </div>
            </div>
          </article>

          <div v-if="isFinishedView && finishedLoading" class="empty-state">正在加载成品库存数据...</div>
          <div v-else-if="isFinishedView && !filteredFinishedItems.length" class="empty-state">没有匹配到成品库存项目。</div>
          <div v-else-if="!isFinishedView && loading" class="empty-state">正在加载库存数据...</div>
          <div v-else-if="!isFinishedView && !filteredItems.length" class="empty-state">没有匹配到库存项目。</div>
        </div>
      </div>

      <details v-if="!isFinishedView && isAuthenticated" class="test-tools-panel">
        <summary>开发测试清理 <small>{{ selectedDeleteIds.length }} 项已勾选</small></summary>
        <div class="selection-toolbar selection-toolbar-inline">
          <label class="checkbox-chip">
            <input :checked="allFilteredSelected" type="checkbox" @change="toggleSelectAllFiltered" />
            <span>全选当前筛选结果</span>
          </label>

          <div class="selection-actions">
            <span>仅用于开发阶段数据清理</span>
            <button class="danger-button" :disabled="deleting || !hasSelectedDeleteItems" type="button" @click="handleBulkDelete">
              {{ deleting ? '删除中...' : '删除勾选库存' }}
            </button>
          </div>
        </div>

        <p class="field-hint dev-note">这里会一并删除库存流水和关联收货关系，正常作业请使用上方台账与作业入口。</p>
      </details>
    </section>

    <section v-if="isFinishedView || isAuthenticated" class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">{{ isFinishedView ? '派生流水' : '流水' }}</p>
          <h3>
            {{
              isFinishedView
                ? selectedFinishedItem
                  ? '由成品库存清单派生的最近记录'
                  : '先从上方选择一个成品'
                : selectedItem
                  ? '最近 12 条记录'
                  : '先从上方选择一个物料'
            }}
          </h3>
        </div>
        <span class="section-meta" v-if="isFinishedView ? selectedFinishedItem : selectedItem">
          {{ isFinishedView ? selectedFinishedItem?.material_name : selectedItem?.material_name }}
        </span>
      </div>

      <div v-if="!isFinishedView" class="link-row sticky-links">
        <RouterLink class="action-link ghost" to="/inventory-import">去做库存导入</RouterLink>
        <RouterLink class="action-link ghost" to="/inventory-export">去做库存导出</RouterLink>
        <RouterLink v-if="selectedItem" class="action-link" :to="{ path: '/receipt', query: { itemId: selectedItem.id, source: 'overview' } }">
          对当前物料入库
        </RouterLink>
        <span v-else class="action-link disabled">先选物料再入库</span>
        <RouterLink v-if="selectedItem" class="action-link secondary" :to="{ path: '/issue', query: { itemId: selectedItem.id, source: 'overview' } }">
          对当前物料出库
        </RouterLink>
        <span v-else class="action-link secondary disabled">先选物料再出库</span>
      </div>

      <div v-else class="receipt-summary emphasis-summary">
        <p>当前为成品库存清单的只读视图，流水由 Excel 中的入库 / 出库字段派生。</p>
        <p>入库记录来自“入库日期 + 入库数量”；出库记录来自三组“出库数量 / 出库时间 / 领用人”。</p>
        <p>本阶段不在这里执行成品收发作业，只用于查询和核对。</p>
      </div>

      <div class="console-table desktop-only">
        <div class="console-table-scroll">
          <div class="console-table-header history-table-grid">
            <span class="console-header-cell">类型</span>
            <span class="console-header-cell">时间</span>
            <span class="console-header-cell">数量</span>
            <span class="console-header-cell">操作人</span>
            <span class="console-header-cell">单号</span>
            <span class="console-header-cell">备注</span>
          </div>

          <article
            v-for="tx in isFinishedView ? finishedTransactions : itemTransactions"
            :key="tx.id"
            class="console-table-row history-table-grid"
          >
            <div class="console-cell">
              <span :class="['console-badge', tx.transaction_type === 'receipt' ? 'ok' : 'warn']">
                {{ tx.transaction_type === 'receipt' ? '入库' : '出库' }}
              </span>
            </div>
            <div class="console-cell muted console-nowrap" :title="tx.occurred_on || '未记录'">{{ tx.occurred_on || '未记录' }}</div>
            <div class="console-cell">
              <strong>{{ tx.quantity }} {{ isFinishedView ? (selectedFinishedItem?.unit || '件') : (selectedItem?.unit || '件') }}</strong>
            </div>
            <div class="console-cell muted console-clamp-2" :title="tx.operator_name || '未填'">{{ tx.operator_name || '未填' }}</div>
            <div class="console-cell muted console-nowrap" :title="tx.reference_code || '未填'">{{ tx.reference_code || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="tx.notes || '无'">{{ tx.notes || '无' }}</div>
          </article>
        </div>

        <div v-if="isFinishedView && finishedHistoryLoading" class="console-empty">正在加载成品派生流水...</div>
        <div v-else-if="isFinishedView && !selectedFinishedItem" class="console-empty">请先从上方成品台账中选择一个对象，再查看派生流水。</div>
        <div v-else-if="isFinishedView && !finishedTransactions.length" class="console-empty">当前成品对象还没有可派生的收发记录。</div>
        <div v-else-if="!isFinishedView && historyLoading" class="console-empty">正在加载流水...</div>
        <div v-else-if="!isFinishedView && !selectedItem" class="console-empty">请先从上方台账中选择一个物料，再查看最近流水。</div>
        <div v-else-if="!isFinishedView && !itemTransactions.length" class="console-empty">当前物料还没有流水记录。</div>
      </div>

      <div class="mobile-only mobile-flow-stack">
        <div class="stack-list">
          <article
            v-for="tx in isFinishedView ? finishedTransactions : itemTransactions"
            :key="tx.id"
            class="data-row mobile-task-card history-mobile-card"
          >
            <div class="data-row-main">
              <div class="data-row-head">
                <span :class="['data-row-badge', tx.transaction_type === 'receipt' ? 'ok' : 'warn']">
                  {{ tx.transaction_type === 'receipt' ? '入库' : '出库' }}
                </span>
                <strong>{{ tx.quantity }} {{ isFinishedView ? (selectedFinishedItem?.unit || '件') : (selectedItem?.unit || '件') }}</strong>
              </div>
              <div class="data-row-meta">
                <span>时间：{{ tx.occurred_on || '未记录' }}</span>
                <span>操作人：{{ tx.operator_name || '未填' }}</span>
                <span>单号：{{ tx.reference_code || '未填' }}</span>
                <span>备注：{{ tx.notes || '无' }}</span>
              </div>
            </div>
          </article>

          <div v-if="isFinishedView && finishedHistoryLoading" class="empty-state">正在加载成品派生流水...</div>
          <div v-else-if="isFinishedView && !selectedFinishedItem" class="empty-state">请先从上方成品台账中选择一个对象，再查看派生流水。</div>
          <div v-else-if="isFinishedView && !finishedTransactions.length" class="empty-state">当前成品对象还没有可派生的收发记录。</div>
          <div v-else-if="!isFinishedView && historyLoading" class="empty-state">正在加载流水...</div>
          <div v-else-if="!isFinishedView && !selectedItem" class="empty-state">请先从上方台账中选择一个物料，再查看最近流水。</div>
          <div v-else-if="!isFinishedView && !itemTransactions.length" class="empty-state">当前物料还没有流水记录。</div>
        </div>
      </div>
    </section>

    <section v-else class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">更多能力</p>
          <h3>登录后开放完整台账与作业</h3>
        </div>
        <span class="section-meta">游客模式</span>
      </div>

      <div class="receipt-summary emphasis-summary">
        <p>当前游客模式只保留物料名称、规格和库存数量查询。</p>
        <p>登录后可查看金额、供应商、区位、最近收发时间和库存流水。</p>
        <p>登录后也会同步开放采购导入、采购收货、直接入库、直接出库和库存维护入口。</p>
      </div>

      <div class="link-row">
        <RouterLink class="action-link primary" to="/login">去登录</RouterLink>
      </div>
    </section>
  </div>
</template>
