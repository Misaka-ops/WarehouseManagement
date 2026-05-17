import { createRouter, createWebHashHistory } from 'vue-router'

import InventoryOverviewPage from './pages/InventoryOverviewPage.vue'
import InventoryImportPage from './pages/InventoryImportPage.vue'
import InventoryExportPage from './pages/InventoryExportPage.vue'
import PurchaseImportPage from './pages/PurchaseImportPage.vue'
import PurchaseReceivingPage from './pages/PurchaseReceivingPage.vue'
import StockOperationPage from './pages/StockOperationPage.vue'
import WorkbenchPage from './pages/WorkbenchPage.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      component: WorkbenchPage,
      meta: {
        eyebrow: 'Workbench',
        title: '工作台',
        description: '从一个总入口查看库存态势，再按工作流进入总览、入库、出库和采购收货页面。',
      },
    },
    {
      path: '/overview',
      component: InventoryOverviewPage,
      meta: {
        eyebrow: 'Inventory',
        title: '仓库总览',
        description: '集中查看库存全貌、定位物料、检查最近流水，并从这里跳转到具体执行页面。',
      },
    },
    {
      path: '/inventory-import',
      component: InventoryImportPage,
      meta: {
        eyebrow: 'Import',
        title: '库存导入',
        description: '从本地上传仓库 Excel 模板，重建当前库存快照，并重新关联采购明细到新库存。',
      },
    },
    {
      path: '/inventory-export',
      component: InventoryExportPage,
      meta: {
        eyebrow: 'Export',
        title: '库存导出',
        description: '把当前库存总览数据导出为仓库原模板格式 Excel，便于继续在线下仓库表中流转。',
      },
    },
    {
      path: '/receipt',
      component: StockOperationPage,
      props: { mode: 'receipt' },
      meta: {
        eyebrow: 'Receipt',
        title: '入库',
        description: '专注做入库登记，减少操作切换，让仓管只围绕收货和补货完成录入。',
      },
    },
    {
      path: '/issue',
      component: StockOperationPage,
      props: { mode: 'issue' },
      meta: {
        eyebrow: 'Issue',
        title: '出库',
        description: '专注做出库登记，优先处理领料和发放，避免在同一页里混合多种动作。',
      },
    },
    {
      path: '/purchase-receiving',
      component: PurchaseReceivingPage,
      meta: {
        eyebrow: 'Purchase',
        title: '采购收货',
        description: '围绕待收货采购明细执行入库，让采购到货与库存入账保持同一步完成。',
      },
    },
    {
      path: '/purchase-import',
      component: PurchaseImportPage,
      meta: {
        eyebrow: 'Purchase Import',
        title: '采购导入',
        description: '从本地采购 Excel 做增量导入，记录每个工作表的上次导入行号，并支持导入后调整清单。',
      },
    },
  ],
})

export default router
