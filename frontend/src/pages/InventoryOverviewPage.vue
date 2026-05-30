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
          <p class="section-kicker">库存态势</p>
          <h3>先看全局，再定位单个物料</h3>
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

      <div class="status-strip workflow-strip">
        <div>
          <span>当前筛选</span>
          <strong>{{ lowStockOnly ? '仅低库存' : '全部库存' }}</strong>
        </div>
        <div>
          <span>当前对象</span>
          <strong>{{ selectedItem?.material_name || '先选择一个物料' }}</strong>
        </div>
        <div>
          <span>下一步</span>
          <strong>{{ selectedItem ? '查看流水或发起入库 / 出库' : '先在下方台账中锁定对象' }}</strong>
        </div>
      </div>
    </section>

    <section class="page-section sticky-head-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">库存台账</p>
          <h3>搜索、筛选并选择作业对象</h3>
        </div>
        <span class="section-meta">{{ filteredItems.length }} / {{ inventoryItems.length }}</span>
      </div>

      <div class="toolbar-grid">
        <label class="field">
          <span>搜索</span>
          <input v-model="searchKeyword" type="text" placeholder="按物料、规格、供应商、区位搜索" />
        </label>

        <button class="soft-button" :class="{ active: lowStockOnly }" type="button" @click="lowStockOnly = !lowStockOnly">
          {{ lowStockOnly ? '当前只看低库存' : '只看低库存' }}
        </button>
      </div>

      <div class="selection-toolbar business-toolbar">
        <div class="selection-status">
          <span>当前作业对象</span>
          <strong>{{ selectedItem?.material_name || '先从下方台账选择物料' }}</strong>
          <small>{{ selectedItem ? `库存 ${selectedItem.quantity_on_hand} ${selectedItem.unit || '件'} / 区位 ${selectedItem.location_name || '未填'}` : '选中后可直接发起入库或出库' }}</small>
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

      <details class="test-tools-panel">
        <summary>测试清理工具 <small>{{ selectedDeleteIds.length }} 项已勾选</small></summary>
        <div class="selection-toolbar selection-toolbar-inline">
          <label class="checkbox-chip">
            <input :checked="allFilteredSelected" type="checkbox" @change="toggleSelectAllFiltered" />
            <span>全选当前筛选结果</span>
          </label>

          <div class="selection-actions">
            <span>仅用于开发清理</span>
            <button class="danger-button" :disabled="deleting || !hasSelectedDeleteItems" type="button" @click="handleBulkDelete">
              {{ deleting ? '删除中...' : '删除勾选库存' }}
            </button>
          </div>
        </div>

        <p class="field-hint dev-note">批量删除仅用于当前测试阶段的数据清理，正常作业请使用上方选中后的作业入口。</p>
      </details>

      <div class="console-table sticky-head-table desktop-only">
        <div class="console-table-scroll">
          <table class="console-data-table">
            <colgroup>
              <col style="width: 56px" />
              <col style="width: 240px" />
              <col style="width: 180px" />
              <col style="width: 90px" />
              <col style="width: 110px" />
              <col style="width: 130px" />
              <col style="width: 130px" />
              <col style="width: 130px" />
              <col style="width: 150px" />
              <col style="width: 150px" />
            </colgroup>
            <thead>
              <tr>
                <th class="console-data-head center">选中</th>
                <th>物料</th>
                <th>规格</th>
                <th>单位</th>
                <th>区位</th>
                <th>采购人</th>
                <th>库存</th>
                <th>金额</th>
                <th>最近入库</th>
                <th>最近出库</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredItems"
                :key="item.id"
                class="console-data-row interactive"
                :class="{ active: item.id === selectedItemId }"
                @click="selectItem(item)"
              >
                <td class="console-data-cell center">
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
                  </div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.specification || '未填'">{{ item.specification || '未填' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.unit || '件'">{{ item.unit || '件' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.location_name || '未填'">{{ item.location_name || '未填' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell">
                    <span :class="['console-badge', Number(item.quantity_on_hand) <= 5 ? 'warn' : 'ok']">
                      {{ item.quantity_on_hand }} {{ item.unit || '件' }}
                    </span>
                  </div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="formatCurrency(item.total_amount)">{{ formatCurrency(item.total_amount) }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.last_receipt_at || '未记录'">{{ item.last_receipt_at || '未记录' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.last_issue_at || '未记录'">{{ item.last_issue_at || '未记录' }}</div>
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
            v-for="item in filteredItems"
            :key="item.id"
            class="data-row clickable triplet mobile-task-card"
            :class="{ active: item.id === selectedItemId }"
            role="button"
            tabindex="0"
            @click="selectItem(item)"
            @keydown.enter.prevent="selectItem(item)"
            @keydown.space.prevent="selectItem(item)"
          >
            <label class="checkbox-chip mobile-select-chip" @click.stop>
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
                <span>区位：{{ item.location_name || '未填' }}</span>
                <span>采购人：{{ item.requester || '未填' }}</span>
                <span>金额：{{ formatCurrency(item.total_amount) }}</span>
                <span>最近入库：{{ item.last_receipt_at || '未记录' }}</span>
                <span>最近出库：{{ item.last_issue_at || '未记录' }}</span>
              </div>
            </div>
          </article>

          <div v-if="loading" class="empty-state">正在加载库存数据...</div>
          <div v-else-if="!filteredItems.length" class="empty-state">没有匹配到库存项目。</div>
        </div>
      </div>
    </section>

    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">流水</p>
          <h3>{{ selectedItem ? '最近 12 条记录' : '先从上方选择一个物料' }}</h3>
        </div>
        <span class="section-meta" v-if="selectedItem">{{ selectedItem.material_name }}</span>
      </div>

      <div class="link-row sticky-links">
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

          <article v-for="tx in itemTransactions" :key="tx.id" class="console-table-row history-table-grid">
            <div class="console-cell">
              <span :class="['console-badge', tx.transaction_type === 'receipt' ? 'ok' : 'warn']">
                {{ tx.transaction_type === 'receipt' ? '入库' : '出库' }}
              </span>
            </div>
            <div class="console-cell muted console-nowrap" :title="tx.occurred_on">{{ tx.occurred_on }}</div>
            <div class="console-cell">
              <strong>{{ tx.quantity }} {{ selectedItem?.unit || '件' }}</strong>
            </div>
            <div class="console-cell muted console-clamp-2" :title="tx.operator_name || '未填'">{{ tx.operator_name || '未填' }}</div>
            <div class="console-cell muted console-nowrap" :title="tx.reference_code || '未填'">{{ tx.reference_code || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="tx.notes || '无'">{{ tx.notes || '无' }}</div>
          </article>
        </div>

        <div v-if="historyLoading" class="console-empty">正在加载流水...</div>
        <div v-else-if="!selectedItem" class="console-empty">请先从上方台账中选择一个物料，再查看最近流水。</div>
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
          <div v-else-if="!selectedItem" class="empty-state">请先从上方台账中选择一个物料，再查看最近流水。</div>
          <div v-else-if="!itemTransactions.length" class="empty-state">当前物料还没有流水记录。</div>
        </div>
      </div>
    </section>
  </div>
</template>
