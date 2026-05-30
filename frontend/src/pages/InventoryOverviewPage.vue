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

    <section class="page-section sticky-head-section">
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

      <div class="console-table sticky-head-table">
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
              <col style="width: 150px" />
              <col style="width: 150px" />
              <col style="width: 160px" />
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
                <th>最近入库</th>
                <th>最近出库</th>
                <th>操作</th>
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
                    <span class="console-subtext">#{{ item.id }}</span>
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
                  <div class="console-cell muted console-nowrap" :title="item.last_receipt_at || '未记录'">{{ item.last_receipt_at || '未记录' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-nowrap" :title="item.last_issue_at || '未记录'">{{ item.last_issue_at || '未记录' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-row-actions" @click.stop>
                    <RouterLink class="console-action ghost" to="/receipt">入库</RouterLink>
                    <RouterLink class="console-action secondary" to="/issue">出库</RouterLink>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="loading" class="console-empty">正在加载库存数据...</div>
        <div v-else-if="!filteredItems.length" class="console-empty">没有匹配到库存项目。</div>
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

      <div class="link-row sticky-links">
        <RouterLink class="action-link ghost" to="/inventory-import">去做库存导入</RouterLink>
        <RouterLink class="action-link ghost" to="/inventory-export">去做库存导出</RouterLink>
        <RouterLink class="action-link" to="/receipt">去做入库</RouterLink>
        <RouterLink class="action-link secondary" to="/issue">去做出库</RouterLink>
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
              <strong>{{ tx.quantity }} {{ selectedItem?.unit || '件' }}</strong>
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
</template>
