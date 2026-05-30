<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'

const { dashboard, inventoryItems, loading, loadDashboard } = useInventoryWorkspace()
const { loadPendingReceipts, pendingReceipts, pendingReceiptsLoading } = usePendingReceipts()

const focusCards = [
  {
    to: '/overview',
    kicker: '库存台账',
    title: '查库存并看流水',
    description: '快速定位物料，核对区位、单位和最近收发记录。',
    action: '进入台账',
  },
  {
    to: '/purchase-receiving',
    kicker: '采购入库',
    title: '处理待收货采购',
    description: '按待收货明细确认收货，避免采购与库存脱节。',
    action: '去收货入库',
  },
  {
    to: '/receipt',
    kicker: '库存作业',
    title: '直接入库',
    description: '处理补货、退货、盘盈等非采购型入库。',
    action: '开始入库',
  },
  {
    to: '/issue',
    kicker: '库存作业',
    title: '直接出库',
    description: '按领用或发放场景登记出库并同步流水。',
    action: '开始出库',
  },
]

const supportCards = [
  {
    to: '/purchase-import',
    kicker: '采购入库',
    title: '采购单导入与同步',
    description: '导入 Excel 或同步飞书，先形成待收货池。',
    action: '导入采购单',
  },
  {
    to: '/inventory-manual',
    kicker: '数据维护',
    title: '手动录入库存',
    description: '补录散件、盘点修正和临时库存。',
    action: '手动录入',
  },
  {
    to: '/inventory-export',
    kicker: '数据维护',
    title: '库存导出',
    description: '导出当前库存，继续线下交接或归档。',
    action: '导出库存',
  },
]

const lowStockItems = computed(() =>
  inventoryItems.value.filter((item) => Number(item.quantity_on_hand) <= 5).slice(0, 6),
)

const pendingPreviewItems = computed(() => pendingReceipts.value.slice(0, 6))

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
  </section>

  <section class="page-section">
    <div class="section-heading">
      <div>
        <p class="section-kicker">高频作业</p>
        <h3>先放最常用的四个入口</h3>
      </div>
      <span class="section-meta">减少来回切页</span>
    </div>

    <div class="module-grid priority-grid">
      <RouterLink v-for="card in focusCards" :key="card.to" :to="card.to" class="module-card">
        <span class="module-kicker">{{ card.kicker }}</span>
        <h4>{{ card.title }}</h4>
        <p>{{ card.description }}</p>
        <strong>{{ card.action }}</strong>
      </RouterLink>
    </div>

    <div class="section-heading secondary-heading">
      <div>
        <p class="section-kicker">辅助入口</p>
        <h3>低频维护和数据交接放在这里</h3>
      </div>
      <span class="section-meta">减少工作台主屏干扰</span>
    </div>

    <div class="module-grid support-grid">
      <RouterLink v-for="card in supportCards" :key="card.to" :to="card.to" class="module-card subdued utility-card">
        <span class="module-kicker">{{ card.kicker }}</span>
        <h4>{{ card.title }}</h4>
        <p>{{ card.description }}</p>
        <strong>{{ card.action }}</strong>
      </RouterLink>
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
          <table class="console-data-table workbench-data-table">
            <colgroup>
              <col style="width: 30%" />
              <col style="width: 26%" />
              <col style="width: 14%" />
              <col style="width: 14%" />
              <col style="width: 16%" />
            </colgroup>
            <thead>
              <tr>
                <th>物料</th>
                <th>规格</th>
                <th>区位</th>
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
                  <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.location_name || '未填区位'">{{ item.location_name || '未填区位' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
                </td>
                <td class="console-data-cell align-right">
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
        <span>点击物料名称可直接进入库存台账定位该物料。</span>
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
          <table class="console-data-table workbench-data-table">
            <colgroup>
              <col style="width: 30%" />
              <col style="width: 22%" />
              <col style="width: 18%" />
              <col style="width: 14%" />
              <col style="width: 16%" />
            </colgroup>
            <thead>
              <tr>
                <th>物料</th>
                <th>规格</th>
                <th>供应商</th>
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
                  <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填供应商'">{{ item.supplier_name || '未填供应商' }}</div>
                </td>
                <td class="console-data-cell">
                  <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
                </td>
                <td class="console-data-cell align-right">
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
