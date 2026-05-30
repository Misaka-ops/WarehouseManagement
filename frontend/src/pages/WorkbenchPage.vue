<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'

const { dashboard, inventoryItems, loading, loadDashboard } = useInventoryWorkspace()
const { loadPendingReceipts, pendingReceipts, pendingReceiptsLoading } = usePendingReceipts()

const primaryActions = [
  {
    to: '/purchase-receiving',
    label: '去处理采购收货',
    tone: 'primary',
  },
  {
    to: '/overview',
    label: '去看库存台账',
    tone: 'ghost',
  },
  {
    to: '/receipt',
    label: '直接入库',
    tone: 'secondary',
  },
  {
    to: '/issue',
    label: '直接出库',
    tone: 'ghost',
  },
]

const maintenanceActions = [
  {
    to: '/purchase-import',
    label: '采购导入',
  },
  {
    to: '/inventory-manual',
    label: '手动录入库存',
  },
  {
    to: '/inventory-export',
    label: '库存导出',
  },
]

const lowStockItems = computed(() =>
  inventoryItems.value.filter((item) => Number(item.quantity_on_hand) <= 5).slice(0, 6),
)

const pendingPreviewItems = computed(() => pendingReceipts.value.slice(0, 6))
const lowStockSummary = computed(() => {
  if (loading.value) {
    return '正在整理低库存预警。'
  }

  if (!lowStockItems.value.length) {
    return '当前没有低库存预警项。'
  }

  return `${dashboard.value?.summary.low_stock_items ?? lowStockItems.value.length} 条低库存，建议优先回台账确认区位和补货路径。`
})
const pendingSummary = computed(() => {
  if (pendingReceiptsLoading.value) {
    return '正在整理待收货明细。'
  }

  if (!pendingReceipts.value.length) {
    return '当前没有待收货采购积压。'
  }

  return `${pendingReceipts.value.length} 条待收货采购，建议优先核对本次到货并完成入库。`
})

const workbenchSummary = computed(() => {
  if (!dashboard.value) {
    return '正在同步库存和采购待办。'
  }

  const lowStockCount = dashboard.value.summary.low_stock_items
  const pendingCount = pendingReceipts.value.length

  if (lowStockCount === 0 && pendingCount === 0) {
    return '当前没有低库存和待收货积压，可以继续执行日常收发作业。'
  }

  return `当前有 ${lowStockCount} 条低库存预警，${pendingCount} 条待收货采购需要处理。`
})

onMounted(async () => {
  await Promise.all([loadDashboard(), loadPendingReceipts()])
})
</script>

<template>
  <section class="page-section hero-section hero-operations">
    <div class="section-heading">
      <div>
        <p class="section-kicker">今日重点</p>
        <h3>先处理待办，再进入具体作业</h3>
      </div>
      <span class="section-meta">工作台</span>
    </div>

    <p class="section-copy">{{ workbenchSummary }}</p>

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
        <span>低库存预警</span>
        <strong>{{ dashboard?.summary.low_stock_items ?? '--' }}</strong>
      </article>
      <article class="metric-card accent">
        <span>待收货采购</span>
        <strong>{{ pendingReceiptsLoading ? '--' : pendingReceipts.length }}</strong>
      </article>
    </div>

    <div class="workbench-lane-grid">
      <article class="workbench-lane urgent">
        <div class="workbench-lane-head">
          <div>
            <p class="section-kicker">库存异常</p>
            <h4>低库存预警</h4>
          </div>
          <span class="console-badge warn">{{ dashboard?.summary.low_stock_items ?? '--' }} 条</span>
        </div>
        <p>{{ lowStockSummary }}</p>
        <div class="workbench-action-row">
          <RouterLink class="action-link ghost" :to="{ path: '/overview', query: { source: 'workbench-low-stock' } }">查看预警对象</RouterLink>
          <RouterLink class="action-link secondary" to="/receipt">直接补录入库</RouterLink>
        </div>
      </article>

      <article class="workbench-lane">
        <div class="workbench-lane-head">
          <div>
            <p class="section-kicker">采购待办</p>
            <h4>待收货采购</h4>
          </div>
          <span class="console-badge info">{{ pendingReceiptsLoading ? '--' : pendingReceipts.length }} 条</span>
        </div>
        <p>{{ pendingSummary }}</p>
        <div class="workbench-action-row">
          <RouterLink class="action-link primary" :to="{ path: '/purchase-receiving', query: { source: 'workbench-pending' } }">进入采购收货</RouterLink>
          <RouterLink class="action-link ghost" to="/purchase-import">继续导入采购</RouterLink>
        </div>
      </article>
    </div>

    <div class="workbench-action-strip">
      <div class="workbench-action-group">
        <span>常用作业</span>
        <div class="workbench-action-row">
          <RouterLink
            v-for="action in primaryActions"
            :key="action.to"
            :to="action.to"
            class="action-link"
            :class="action.tone"
          >
            {{ action.label }}
          </RouterLink>
        </div>
      </div>

      <div class="workbench-action-group compact">
        <span>补录与交接</span>
        <div class="workbench-action-row">
          <RouterLink v-for="action in maintenanceActions" :key="action.to" :to="action.to" class="action-link ghost">
            {{ action.label }}
          </RouterLink>
        </div>
      </div>
    </div>
  </section>

  <div class="dual-grid">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">库存预警</p>
          <h3>优先核对低库存</h3>
        </div>
        <span class="section-meta">{{ loading ? '加载中' : `预览 ${lowStockItems.length} / ${dashboard?.summary.low_stock_items ?? 0} 条` }}</span>
      </div>

      <div class="console-table desktop-only">
        <div class="console-table-scroll workbench-table-scroll">
          <table class="console-data-table dense-table workbench-data-table">
            <colgroup>
              <col style="width: 38%" />
              <col style="width: 28%" />
              <col style="width: 16%" />
              <col style="width: 18%" />
            </colgroup>
            <thead>
              <tr>
                <th>物料</th>
                <th>规格 / 区位</th>
                <th>采购人</th>
                <th class="align-right">库存</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in lowStockItems" :key="item.id">
                <td class="console-data-cell">
                  <div class="console-cell">
                    <RouterLink class="workbench-inline-link" :to="{ path: '/overview', query: { itemId: item.id, source: 'workbench-low-stock' } }">
                      <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
                    </RouterLink>
                  </div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell">
                    <span class="muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</span>
                    <small class="console-subline" :title="item.location_name || '未填区位'">区位：{{ item.location_name || '未填区位' }}</small>
                  </div>
                </td>
                <td class="console-data-cell v-middle">
                  <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
                </td>
                <td class="console-data-cell align-right v-middle">
                  <span class="console-badge warn">{{ item.quantity_on_hand }} {{ item.unit || '件' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!loading && !lowStockItems.length" class="console-empty">当前没有低库存预警项。</div>
        <div v-if="loading" class="console-empty">正在加载库存态势...</div>
      </div>

      <div class="mobile-only mobile-flow-stack">
        <div class="stack-list">
          <RouterLink
            v-for="item in lowStockItems"
            :key="item.id"
            class="data-row clickable triplet mobile-task-card"
            :to="{ path: '/overview', query: { itemId: item.id, source: 'workbench-low-stock' } }"
          >
            <div class="data-row-main">
              <div class="data-row-head">
                <strong>{{ item.material_name }}</strong>
                <span class="data-row-badge warn">{{ item.quantity_on_hand }} {{ item.unit || '件' }}</span>
              </div>
              <div class="data-row-meta">
                <span>规格：{{ item.specification || '未填规格' }}</span>
                <span>区位：{{ item.location_name || '未填区位' }}</span>
                <span>采购人：{{ item.requester || '未填' }}</span>
              </div>
            </div>
          </RouterLink>

          <div v-if="!loading && !lowStockItems.length" class="empty-state">当前没有低库存预警项。</div>
          <div v-if="loading" class="empty-state">正在加载库存态势...</div>
        </div>
      </div>

      <div class="console-table-caption">
        <span>点击物料名称可直接带着上下文回到库存台账定位该物料。</span>
        <RouterLink class="action-link ghost" :to="{ path: '/overview', query: { source: 'workbench-low-stock' } }">查看完整台账</RouterLink>
      </div>
    </section>

    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">采购待办</p>
          <h3>待收货采购优先收尾</h3>
        </div>
        <span class="section-meta">{{ pendingReceiptsLoading ? '加载中' : `预览 ${pendingPreviewItems.length} / ${pendingReceipts.length} 条` }}</span>
      </div>

      <div class="console-table desktop-only">
        <div class="console-table-scroll workbench-table-scroll">
          <table class="console-data-table dense-table workbench-data-table">
            <colgroup>
              <col style="width: 38%" />
              <col style="width: 28%" />
              <col style="width: 16%" />
              <col style="width: 18%" />
            </colgroup>
            <thead>
              <tr>
                <th>物料</th>
                <th>规格 / 供应商</th>
                <th>请购人</th>
                <th class="align-right">待收数量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in pendingPreviewItems" :key="item.purchase_item_id">
                <td class="console-data-cell">
                  <div class="console-cell">
                    <RouterLink
                      class="workbench-inline-link"
                      :to="{ path: '/purchase-receiving', query: { purchaseItemId: item.purchase_item_id, source: 'workbench-pending' } }"
                    >
                      <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
                    </RouterLink>
                  </div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell">
                    <span class="muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</span>
                    <small class="console-subline" :title="item.supplier_name || '未填供应商'">供应商：{{ item.supplier_name || '未填供应商' }}</small>
                  </div>
                </td>
                <td class="console-data-cell v-middle">
                  <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
                </td>
                <td class="console-data-cell align-right v-middle">
                  <span class="console-badge info">{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!pendingReceiptsLoading && !pendingReceipts.length" class="console-empty">当前没有待收货采购明细。</div>
        <div v-if="pendingReceiptsLoading" class="console-empty">正在加载待收货明细...</div>
      </div>

      <div class="mobile-only mobile-flow-stack">
        <div class="stack-list">
          <RouterLink
            v-for="item in pendingPreviewItems"
            :key="item.purchase_item_id"
            class="data-row clickable triplet mobile-task-card"
            :to="{ path: '/purchase-receiving', query: { purchaseItemId: item.purchase_item_id, source: 'workbench-pending' } }"
          >
            <div class="data-row-main">
              <div class="data-row-head">
                <strong>{{ item.material_name }}</strong>
                <span class="data-row-badge ok">{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
              </div>
              <div class="data-row-meta">
                <span>规格：{{ item.specification || '未填规格' }}</span>
                <span>供应商：{{ item.supplier_name || '未填供应商' }}</span>
                <span>请购人：{{ item.requester || '未填' }}</span>
              </div>
            </div>
          </RouterLink>

          <div v-if="!pendingReceiptsLoading && !pendingReceipts.length" class="empty-state">当前没有待收货采购明细。</div>
          <div v-if="pendingReceiptsLoading" class="empty-state">正在加载待收货明细...</div>
        </div>
      </div>

      <div class="console-table-caption">
        <span>点击物料名称可直接带入采购收货页继续处理。</span>
        <RouterLink class="action-link ghost" :to="{ path: '/purchase-receiving', query: { source: 'workbench-pending' } }">查看完整待收货列表</RouterLink>
      </div>
    </section>
  </div>
</template>
