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
        description: '库存态势与快捷入口。',
      },
    },
    {
      path: '/overview',
      component: InventoryOverviewPage,
      meta: {
        eyebrow: 'Inventory',
        title: '仓库总览',
        description: '查看库存和最近流水。',
      },
    },
    {
      path: '/inventory-import',
      component: InventoryImportPage,
      meta: {
        eyebrow: 'Import',
        title: '库存导入',
        description: '导入仓库库存 Excel。',
      },
    },
    {
      path: '/inventory-export',
      component: InventoryExportPage,
      meta: {
        eyebrow: 'Export',
        title: '库存导出',
        description: '导出当前库存 Excel。',
      },
    },
    {
      path: '/receipt',
      component: StockOperationPage,
      props: { mode: 'receipt' },
      meta: {
        eyebrow: 'Receipt',
        title: '入库',
        description: '登记入库。',
      },
    },
    {
      path: '/issue',
      component: StockOperationPage,
      props: { mode: 'issue' },
      meta: {
        eyebrow: 'Issue',
        title: '出库',
        description: '登记出库。',
      },
    },
    {
      path: '/purchase-receiving',
      component: PurchaseReceivingPage,
      meta: {
        eyebrow: 'Purchase',
        title: '采购收货',
        description: '按采购明细收货入库。',
      },
    },
    {
      path: '/purchase-import',
      component: PurchaseImportPage,
      meta: {
        eyebrow: 'Purchase Import',
        title: '采购导入',
        description: '导入采购 Excel。',
      },
    },
  ],
})

export default router
