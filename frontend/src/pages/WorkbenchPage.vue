<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'

const { dashboard, inventoryItems, loading, loadDashboard } = useInventoryWorkspace()
const { loadPendingReceipts, pendingReceipts, pendingReceiptsLoading } = usePendingReceipts()

const todayLabel = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(new Date())

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
        <p class="section-kicker">今日工作台</p>
        <h3>把仓库操作拆成几个明确入口</h3>
      </div>
      <span class="section-meta">{{ todayLabel }}</span>
    </div>

    <p class="section-copy">
      主页只负责给你一个清晰的出发点。先看库存态势，再决定去仓库总览、入库、出库还是采购收货页面，避免所有动作挤在一个界面里。
    </p>

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
  </section>

  <section class="page-section">
    <div class="section-heading">
      <div>
        <p class="section-kicker">功能入口</p>
        <h3>按工作流进入页面</h3>
      </div>
      <span class="section-meta">减少同页混杂操作</span>
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

      <div class="stack-list">
        <article v-for="item in lowStockItems" :key="item.id" class="list-card warm">
          <div>
            <strong>{{ item.material_name }}</strong>
            <p>{{ item.specification || '未填规格' }}</p>
          </div>
          <span>{{ item.quantity_on_hand }} {{ item.unit || '件' }}</span>
        </article>

        <div v-if="!loading && !lowStockItems.length" class="empty-state">当前没有低库存预警项。</div>
        <div v-if="loading" class="empty-state">正在加载库存态势...</div>
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

      <div class="stack-list">
        <article v-for="item in pendingReceipts.slice(0, 6)" :key="item.purchase_item_id" class="list-card cool">
          <div>
            <strong>{{ item.material_name }}</strong>
            <p>{{ item.supplier_name || '未填供应商' }}</p>
          </div>
          <span>{{ item.pending_quantity }} {{ item.unit || '件' }}</span>
        </article>

        <div v-if="!pendingReceiptsLoading && !pendingReceipts.length" class="empty-state">当前没有待收货采购明细。</div>
        <div v-if="pendingReceiptsLoading" class="empty-state">正在加载待收货明细...</div>
      </div>
    </section>
  </div>
</template>
