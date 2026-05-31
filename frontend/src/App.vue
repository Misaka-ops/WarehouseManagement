<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from './composables/useAuth'

type NavItem = {
  to: string
  kicker: string
  label: string
  requiresAuth?: boolean
}

type NavGroup = {
  title: string
  items: NavItem[]
}

type ShortcutTone = 'primary' | 'secondary' | 'ghost'

type PageShortcut = {
  label: string
  to: string
  tone?: ShortcutTone
}

const route = useRoute()
const router = useRouter()
const { currentUser, isAuthenticated, logout } = useAuth()
const navExpanded = ref(false)

const navGroups: NavGroup[] = [
  {
    title: '工作台',
    items: [{ to: '/', kicker: 'Overview', label: '工作台', requiresAuth: true }],
  },
  {
    title: '库存查询',
    items: [{ to: '/overview', kicker: 'Inspect', label: '库存查询与台账' }],
  },
  {
    title: '采购流程',
    items: [
      { to: '/purchase-import', kicker: 'Prepare', label: '采购导入与同步', requiresAuth: true },
      { to: '/purchase-receiving', kicker: 'Receive', label: '采购收货入库', requiresAuth: true },
    ],
  },
  {
    title: '直接作业',
    items: [
      { to: '/receipt', kicker: 'Receipt', label: '直接入库', requiresAuth: true },
      { to: '/issue', kicker: 'Issue', label: '直接出库', requiresAuth: true },
      { to: '/inventory-manual', kicker: 'Manual', label: '手动录入库存', requiresAuth: true },
    ],
  },
  {
    title: '数据维护',
    items: [
      { to: '/inventory-import', kicker: 'Import', label: '库存导入', requiresAuth: true },
      { to: '/inventory-export', kicker: 'Export', label: '库存导出', requiresAuth: true },
    ],
  },
]

const visibleNavGroups = computed(() =>
  navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => isAuthenticated.value || !item.requiresAuth),
    }))
    .filter((group) => group.items.length > 0),
)

const sourceLabelMap: Record<string, string> = {
  'workbench-low-stock': '工作台低库存',
  'workbench-pending': '工作台采购待办',
  overview: '库存台账',
  'purchase-import': '采购导入',
}

const pageEyebrow = computed(() => String(route.meta.eyebrow ?? '仓储运营'))
const pageTitle = computed(() => String(route.meta.title ?? '仓储控制台'))
const pageDescription = computed(() => String(route.meta.description ?? ''))
const pageModule = computed(() => String(route.meta.module ?? pageEyebrow.value))
const pageGuide = computed(() => String(route.meta.guide ?? ''))
const pageStatusLabel = computed(() => String(route.meta.statusLabel ?? '执行中'))
const bannerSummary = computed(() => pageDescription.value.trim())
const bannerGuideLabel = computed(() => {
  const guide = pageGuide.value.trim()
  return guide !== bannerSummary.value ? guide : ''
})
const pageShortcuts = computed<PageShortcut[]>(() => {
  const shortcuts = route.meta.shortcuts
  if (!Array.isArray(shortcuts)) {
    return []
  }

  return (shortcuts as PageShortcut[]).filter((shortcut) => isAuthenticated.value || !router.resolve(shortcut.to).meta.requiresAuth)
})
const sourceContextLabel = computed(() => {
  const sourceKey = typeof route.query.source === 'string' ? route.query.source : ''
  return sourceLabelMap[sourceKey] ?? ''
})
const itemContextLabel = computed(() => {
  const itemId = typeof route.query.itemId === 'string' ? route.query.itemId : ''
  return itemId ? `#${itemId}` : ''
})
const purchaseItemContextLabel = computed(() => {
  const purchaseItemId = typeof route.query.purchaseItemId === 'string' ? route.query.purchaseItemId : ''
  return purchaseItemId ? `#${purchaseItemId}` : ''
})
const purchaseItemScopeCount = computed(() => {
  const rawValue = typeof route.query.purchaseItemIds === 'string' ? route.query.purchaseItemIds : ''
  if (!rawValue.trim()) {
    return 0
  }

  return [...new Set(rawValue.split(',').map((value) => Number(value.trim())).filter((value) => Number.isFinite(value) && value > 0))].length
})
const bannerPulseNote = computed(() => {
  if (purchaseItemScopeCount.value > 1) {
    return `当前正在处理本次带入的 ${purchaseItemScopeCount.value} 条采购明细。`
  }

  if (purchaseItemContextLabel.value) {
    return `已带入采购明细 ${purchaseItemContextLabel.value}，可直接核对收货。`
  }

  if (itemContextLabel.value) {
    return `已带入物料 ${itemContextLabel.value}，可直接查看流水或发起作业。`
  }

  if (sourceContextLabel.value) {
    return `当前来源：${sourceContextLabel.value}`
  }

  return bannerGuideLabel.value || '当前页面可直接开始作业'
})

const contextChips = computed(() => {
  const chips: Array<{ label: string; value: string }> = [{ label: '模块', value: pageModule.value }]
  if (sourceContextLabel.value) {
    chips.push({ label: '来源', value: sourceContextLabel.value })
  }

  if (itemContextLabel.value) {
    chips.push({ label: '物料', value: itemContextLabel.value })
  }

  if (purchaseItemContextLabel.value) {
    chips.push({ label: '采购明细', value: purchaseItemContextLabel.value })
  }

  if (purchaseItemScopeCount.value > 1) {
    chips.push({ label: '采购范围', value: `${purchaseItemScopeCount.value} 条` })
  }

  if (route.path === '/receipt' || route.path === '/issue') {
    chips.push({ label: '模式', value: pageTitle.value })
  }

  return chips
})

watch(
  () => route.path,
  () => {
    navExpanded.value = false
  },
)

async function handleLogout() {
  logout()
  if (route.path !== '/overview') {
    await router.replace('/overview')
  }
}
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar-shell">
      <div class="brand-panel">
        <p class="eyebrow">WAREHOUSE OPS</p>
        <h1>仓储运营台</h1>
        <p class="brand-copy">对象先定位，再执行收发和采购入库。</p>
      </div>

      <div class="banner-pulse sidebar-auth-card">
        <span>{{ isAuthenticated ? '当前账号' : '游客模式' }}</span>
        <strong>{{ isAuthenticated ? currentUser?.username : '仅开放库存台账查询' }}</strong>
        <small>{{ isAuthenticated ? '已解锁全部库存与采购操作。' : '登录后可查看金额、供应商并使用全部功能。' }}</small>
        <RouterLink v-if="!isAuthenticated" class="action-link primary" to="/login">管理员登录</RouterLink>
        <button v-else class="action-link ghost auth-action-button" type="button" @click="handleLogout">退出登录</button>
      </div>

      <button class="nav-toggle" type="button" :aria-expanded="navExpanded" aria-controls="primary-nav-groups" @click="navExpanded = !navExpanded">
        <span class="nav-toggle-label">导航 / {{ pageTitle }}</span>
        <span class="nav-toggle-state">{{ navExpanded ? '收起' : '展开' }}</span>
      </button>

      <div id="primary-nav-groups" class="nav-groups" :class="{ expanded: navExpanded }">
        <section v-for="group in visibleNavGroups" :key="group.title" class="nav-group">
          <p class="nav-group-title">{{ group.title }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            :class="{ active: route.path === item.to }"
          >
            <span class="nav-kicker">{{ item.kicker }}</span>
            <strong>{{ item.label }}</strong>
          </RouterLink>
        </section>
      </div>
    </aside>

    <div class="page-shell">
      <header class="page-banner">
        <div class="banner-main">
          <div class="banner-breadcrumb">
            <span>{{ pageModule }}</span>
            <span>/</span>
            <strong>{{ pageTitle }}</strong>
          </div>

          <p class="eyebrow">{{ pageEyebrow }}</p>
          <h2>{{ pageTitle }}</h2>
          <p v-if="bannerSummary" class="banner-summary">{{ bannerSummary }}</p>
          <p v-if="bannerGuideLabel" class="banner-guide">{{ bannerGuideLabel }}</p>

          <div v-if="contextChips.length" class="context-chip-row">
            <span v-for="chip in contextChips" :key="`${chip.label}-${chip.value}`" class="context-chip">
              <small>{{ chip.label }}</small>
              <strong>{{ chip.value }}</strong>
            </span>
          </div>
        </div>

        <div class="banner-side">
          <div v-if="pageShortcuts.length" class="banner-actions">
            <RouterLink
              v-for="shortcut in pageShortcuts"
              :key="`${pageTitle}-${shortcut.to}-${shortcut.label}`"
              :to="shortcut.to"
              class="action-link"
              :class="shortcut.tone ?? 'ghost'"
            >
              {{ shortcut.label }}
            </RouterLink>
          </div>

          <div class="banner-pulse">
            <span>当前阶段</span>
            <strong>{{ pageStatusLabel }}</strong>
            <small>{{ bannerPulseNote }}</small>
          </div>
        </div>
      </header>

      <main class="page-body">
        <RouterView />
      </main>
    </div>
  </div>
</template>
