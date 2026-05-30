<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'

const { dashboard, inventoryItems, loading, loadDashboard } = useInventoryWorkspace()
const { loadPendingReceipts, pendingReceipts, pendingReceiptsLoading } = usePendingReceipts()

const moduleCards = [
  {
    to: '/overview',
    kicker: '总览',
    title: '仓库总览',
    description: '快速搜索物料、检查库存状态、查看最近流水。',
    action: '进入总览',
  },
  {
    to: '/inventory-import',
    kicker: '导入',
    title: '库存导入',
    description: '从本地上传仓库 Excel 模板，按当前模板重建库存快照。',
    action: '上传 Excel',
  },
  {
    to: '/inventory-export',
    kicker: '导出',
    title: '库存导出',
    description: '把当前库存总览导出成仓库原模板 Excel，继续在线下表单中流转。',
    action: '下载 Excel',
  },
  {
    to: '/inventory-manual',
    kicker: '维护',
    title: '手动录入库存',
    description: '直接补录散件或临时库存，支持新建与按相同物料累加。',
    action: '开始录入',
  },
  {
    to: '/purchase-import',
    kicker: '采购',
    title: '采购导入',
    description: '按采购 Excel 上次导入行号做增量导入，导入后可手工调整明细。',
    action: '导入采购',
  },
  {
    to: '/receipt',
    kicker: '执行',
    title: '入库',
    description: '将补货、退货、盘盈等入库动作聚焦到一页完成。',
    action: '开始入库',
  },
  {
    to: '/issue',
    kicker: '执行',
    title: '出库',
    description: '按领料和发放流程登记出库，减少误操作。',
    action: '开始出库',
  },
  {
    to: '/purchase-receiving',
    kicker: '采购',
    title: '采购收货',
    description: '直接从待收货采购明细入库，保持采购与库存同步。',
    action: '去收货',
  },
]

const lowStockItems = computed(() =>
  inventoryItems.value.filter((item) => Number(item.quantity_on_hand) <= 5).slice(0, 6),
)

onMounted(async () => {
  await Promise.all([loadDashboard(), loadPendingReceipts()])
})
</script>

<template>
  <section class="page-section hero-section">
    <div class="section-heading">
      <div>
        <p class="section-kicker">工作台</p>
        <h3>库存态势</h3>
      </div>
      <span class="section-meta">总览</span>
    </div>

    <div class="metric-grid">
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

    <div class="status-strip">
      <div>
        <span>当前关注</span>
        <strong>{{ dashboard ? '库存与待收货' : '加载中' }}</strong>
      </div>
      <div>
        <span>低库存</span>
        <strong>{{ dashboard?.summary.low_stock_items ?? '--' }}</strong>
      </div>
      <div>
        <span>待收货</span>
        <strong>{{ pendingReceiptsLoading ? '--' : pendingReceipts.length }}</strong>
      </div>
    </div>
  </section>

  <section class="page-section">
    <div class="section-heading">
      <div>
        <p class="section-kicker">快捷入口</p>
        <h3>常用操作</h3>
      </div>
      <span class="section-meta">导航</span>
    </div>

    <div class="module-grid">
      <RouterLink v-for="card in moduleCards" :key="card.to" :to="card.to" class="module-card">
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
          <p class="section-kicker">预警</p>
          <h3>低库存物料</h3>
        </div>
        <span class="section-meta">{{ loading ? '加载中' : `${lowStockItems.length} 条` }}</span>
      </div>

      <div class="console-table">
        <div class="console-table-scroll">
          <div class="console-table-header summary-table-grid">
            <span class="console-header-cell">物料</span>
            <span class="console-header-cell">规格</span>
            <span class="console-header-cell">项目</span>
            <span class="console-header-cell">采购人</span>
            <span class="console-header-cell">库存</span>
            <span class="console-header-cell">操作</span>
          </div>

          <article v-for="item in lowStockItems" :key="item.id" class="console-table-row summary-table-grid">
            <div class="console-cell">
              <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
              <span class="console-subtext">#{{ item.id }}</span>
            </div>
            <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.project_name || '未填项目'">{{ item.project_name || '未填项目' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
            <div class="console-cell">
              <span class="console-badge warn">{{ item.quantity_on_hand }} {{ item.unit || '件' }}</span>
            </div>
            <div class="console-row-actions">
              <RouterLink class="console-action primary" to="/receipt">入库</RouterLink>
              <RouterLink class="console-action secondary" to="/issue">出库</RouterLink>
            </div>
          </article>
        </div>

        <div v-if="!loading && !lowStockItems.length" class="console-empty">当前没有低库存预警项。</div>
        <div v-if="loading" class="console-empty">正在加载库存态势...</div>
      </div>
    </section>

    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">待办</p>
          <h3>采购待收货</h3>
        </div>
        <span class="section-meta">{{ pendingReceiptsLoading ? '加载中' : `${pendingReceipts.length} 条` }}</span>
      </div>

      <div class="console-table">
        <div class="console-table-scroll">
          <div class="console-table-header summary-table-grid">
            <span class="console-header-cell">物料</span>
            <span class="console-header-cell">规格</span>
            <span class="console-header-cell">供应商</span>
            <span class="console-header-cell">采购人</span>
            <span class="console-header-cell">待收数量</span>
            <span class="console-header-cell">操作</span>
          </div>

          <article v-for="item in pendingReceipts.slice(0, 6)" :key="item.purchase_item_id" class="console-table-row summary-table-grid">
            <div class="console-cell">
              <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
              <span class="console-subtext">#{{ item.purchase_item_id }}</span>
            </div>
            <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填供应商'">{{ item.supplier_name || '未填供应商' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.requester || '未填'">{{ item.requester || '未填' }}</div>
            <div class="console-cell">
              <span class="console-badge info">{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
            </div>
            <div class="console-row-actions">
              <RouterLink class="console-action primary" to="/purchase-receiving">收货</RouterLink>
            </div>
          </article>
        </div>

        <div v-if="!pendingReceiptsLoading && !pendingReceipts.length" class="console-empty">当前没有待收货采购明细。</div>
        <div v-if="pendingReceiptsLoading" class="console-empty">正在加载待收货明细...</div>
      </div>
    </section>
  </div>
</template>
