import { createRouter, createWebHashHistory } from 'vue-router'

import InventoryOverviewPage from './pages/InventoryOverviewPage.vue'
import InventoryImportPage from './pages/InventoryImportPage.vue'
import InventoryExportPage from './pages/InventoryExportPage.vue'
import ManualInventoryPage from './pages/ManualInventoryPage.vue'
import LoginPage from './pages/LoginPage.vue'
import PurchaseImportPage from './pages/PurchaseImportPage.vue'
import PurchaseReceivingPage from './pages/PurchaseReceivingPage.vue'
import SettingsFeishuPage from './pages/SettingsFeishuPage.vue'
import StockOperationPage from './pages/StockOperationPage.vue'
import WorkbenchPage from './pages/WorkbenchPage.vue'
import { useAuth } from './composables/useAuth'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      component: WorkbenchPage,
      meta: {
        requiresAuth: true,
        eyebrow: '工作台',
        title: '工作台',
        description: '待办、预警与常用作业入口。',
        module: '总控工作台',
        guide: '先处理低库存与待收货，再进入具体收发作业。',
        statusLabel: '日常值守',
        shortcuts: [
          { label: '库存台账', to: '/overview', tone: 'ghost' },
          { label: '采购收货', to: '/purchase-receiving', tone: 'primary' },
          { label: '直接出库', to: '/issue', tone: 'secondary' },
        ],
      },
    },
    {
      path: '/overview',
      component: InventoryOverviewPage,
      meta: {
        eyebrow: '库存台账',
        title: '库存查询与台账',
        description: '查库存、看流水，并快速发起库存作业。',
        module: '库存查询',
        guide: '先搜索并锁定物料，再查看流水或发起入库、出库。',
        statusLabel: '库存核对',
        shortcuts: [
          { label: '直接入库', to: '/receipt', tone: 'primary' },
          { label: '直接出库', to: '/issue', tone: 'secondary' },
          { label: '导出库存', to: '/inventory-export', tone: 'ghost' },
        ],
      },
    },
    {
      path: '/inventory-import',
      component: InventoryImportPage,
      meta: {
        requiresAuth: true,
        eyebrow: '数据维护',
        title: '库存导入',
        description: '用仓库模板重建当前库存快照。',
        module: '数据维护',
        guide: '适合重建库存快照，导入后再回到台账检查结果。',
        statusLabel: '库存重建',
        shortcuts: [
          { label: '库存台账', to: '/overview', tone: 'ghost' },
          { label: '手动录入', to: '/inventory-manual', tone: 'secondary' },
        ],
      },
    },
    {
      path: '/inventory-export',
      component: InventoryExportPage,
      meta: {
        requiresAuth: true,
        eyebrow: '数据维护',
        title: '库存导出',
        description: '导出当前库存并延续线下表单流转。',
        module: '数据维护',
        guide: '导出前建议先在库存台账确认当前筛选对象与库存状态。',
        statusLabel: '库存交接',
        shortcuts: [
          { label: '库存台账', to: '/overview', tone: 'ghost' },
          { label: '库存导入', to: '/inventory-import', tone: 'secondary' },
        ],
      },
    },
    {
      path: '/inventory-manual',
      component: ManualInventoryPage,
      meta: {
        requiresAuth: true,
        eyebrow: '库存作业',
        title: '手动录入库存',
        description: '直接新建或补录散件库存，并自动写入库存流水。',
        module: '直接作业',
        guide: '先识别库存项，再填写本次入库字段，避免误并入已有库存。',
        statusLabel: '手动补录',
        shortcuts: [
          { label: '库存台账', to: '/overview', tone: 'ghost' },
          { label: '直接入库', to: '/receipt', tone: 'primary' },
        ],
      },
    },
    {
      path: '/receipt',
      component: StockOperationPage,
      props: { mode: 'receipt' },
      meta: {
        requiresAuth: true,
        eyebrow: '库存作业',
        title: '直接入库',
        description: '登记补货、退货、盘盈等非采购收货入库。',
        module: '直接作业',
        guide: '先选择库存对象，再填写数量、日期和单号。',
        statusLabel: '直接入库',
        shortcuts: [
          { label: '库存台账', to: '/overview', tone: 'ghost' },
          { label: '采购收货', to: '/purchase-receiving', tone: 'secondary' },
        ],
      },
    },
    {
      path: '/issue',
      component: StockOperationPage,
      props: { mode: 'issue' },
      meta: {
        requiresAuth: true,
        eyebrow: '库存作业',
        title: '直接出库',
        description: '按物料执行领用、发放和其他出库。',
        module: '直接作业',
        guide: '先确认库存余量，再登记本次出库信息。',
        statusLabel: '直接出库',
        shortcuts: [
          { label: '库存台账', to: '/overview', tone: 'ghost' },
          { label: '直接入库', to: '/receipt', tone: 'secondary' },
        ],
      },
    },
    {
      path: '/purchase-receiving',
      component: PurchaseReceivingPage,
      meta: {
        requiresAuth: true,
        eyebrow: '采购入库',
        title: '采购收货入库',
        description: '从待收货采购明细确认收货并写入库存。',
        module: '采购流程',
        guide: '先确认待收货对象，再复核本次会影响哪些采购明细。',
        statusLabel: '待收货处理',
        shortcuts: [
          { label: '采购导入', to: '/purchase-import', tone: 'ghost' },
          { label: '库存台账', to: '/overview', tone: 'secondary' },
        ],
      },
    },
    {
      path: '/purchase-import',
      component: PurchaseImportPage,
      meta: {
        requiresAuth: true,
        eyebrow: '采购入库',
        title: '采购单导入与同步',
        description: '导入 Excel 或同步飞书采购单，形成待收货列表。',
        module: '采购流程',
        guide: '先形成待收货池，再进入采购收货做正式入库。',
        statusLabel: '采购准备',
        shortcuts: [
          { label: '采购收货', to: '/purchase-receiving', tone: 'primary' },
          { label: '库存台账', to: '/overview', tone: 'ghost' },
        ],
      },
    },
    {
      path: '/settings/feishu',
      component: SettingsFeishuPage,
      meta: {
        requiresAuth: true,
        eyebrow: '系统设置',
        title: '飞书配置',
        description: '维护飞书采购同步所需的 App 凭证与审批编码。',
        module: '系统设置',
        guide: '保存后下一次飞书同步会直接使用这里的配置。',
        statusLabel: '配置维护',
        shortcuts: [
          { label: '采购导入', to: '/purchase-import', tone: 'primary' },
          { label: '库存台账', to: '/overview', tone: 'ghost' },
        ],
      },
    },
    {
      path: '/login',
      component: LoginPage,
      meta: {
        guestOnly: true,
        eyebrow: '账号登录',
        title: '管理员登录',
        description: '登录后可查看金额、供应商并使用全部库存与采购操作。',
        module: '权限控制',
        guide: '游客模式仅开放库存台账基础查询。',
        statusLabel: '权限验证',
        shortcuts: [{ label: '先看库存台账', to: '/overview', tone: 'ghost' }],
      },
    },
  ],
})

router.beforeEach((to) => {
  const { isAuthenticated } = useAuth()

  if (to.path === '/' && !isAuthenticated.value) {
    return { path: '/overview' }
  }

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return {
      path: '/login',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  if (to.meta.guestOnly && isAuthenticated.value) {
    const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/') ? to.query.redirect : '/'
    return redirect
  }

  return true
})

export default router
