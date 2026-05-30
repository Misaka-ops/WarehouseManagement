<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

type NavItem = {
  to: string
  kicker: string
  label: string
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
const navExpanded = ref(false)

const navGroups: NavGroup[] = [
  {
    title: '工作台',
    items: [{ to: '/', kicker: 'Overview', label: '工作台' }],
  },
  {
    title: '查询与核对',
    items: [{ to: '/overview', kicker: 'Inspect', label: '库存查询与台账' }],
  },
  {
    title: '执行作业',
    items: [
      { to: '/purchase-receiving', kicker: 'Purchase', label: '采购收货入库' },
      { to: '/receipt', kicker: 'Receipt', label: '直接入库' },
      { to: '/issue', kicker: 'Issue', label: '直接出库' },
    ],
  },
  {
    title: '准备与维护',
    items: [
      { to: '/purchase-import', kicker: 'Prepare', label: '采购导入与同步' },
      { to: '/inventory-manual', kicker: 'Manual', label: '手动录入库存' },
      { to: '/inventory-import', kicker: 'Import', label: '库存导入' },
      { to: '/inventory-export', kicker: 'Export', label: '库存导出' },
    ],
  },
]

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
const bannerSummary = computed(() => {
  const description = pageDescription.value.trim()
  const guide = pageGuide.value.trim()

  if (description && guide && description !== guide) {
    return `${description} ${guide}`
  }

  return guide || description
})
const pageShortcuts = computed<PageShortcut[]>(() => {
  const shortcuts = route.meta.shortcuts
  return Array.isArray(shortcuts) ? (shortcuts as PageShortcut[]) : []
})

const contextChips = computed(() => {
  const chips: Array<{ label: string; value: string }> = [{ label: '模块', value: pageModule.value }]
  const sourceKey = typeof route.query.source === 'string' ? route.query.source : ''
  if (sourceKey && sourceLabelMap[sourceKey]) {
    chips.push({ label: '来源', value: sourceLabelMap[sourceKey] })
  }

  const itemId = typeof route.query.itemId === 'string' ? route.query.itemId : ''
  if (itemId) {
    chips.push({ label: '物料', value: `#${itemId}` })
  }

  const purchaseItemId = typeof route.query.purchaseItemId === 'string' ? route.query.purchaseItemId : ''
  if (purchaseItemId) {
    chips.push({ label: '采购明细', value: `#${purchaseItemId}` })
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
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar-shell">
      <div class="brand-panel">
        <p class="eyebrow">WAREHOUSE OPS</p>
        <h1>仓储运营台</h1>
        <p class="brand-copy">库存清晰、操作稳定、采购收货可追踪</p>
      </div>

      <button class="nav-toggle" type="button" :aria-expanded="navExpanded" aria-controls="primary-nav-groups" @click="navExpanded = !navExpanded">
        <span class="nav-toggle-label">导航 / {{ pageTitle }}</span>
        <span class="nav-toggle-state">{{ navExpanded ? '收起' : '展开' }}</span>
      </button>

      <div id="primary-nav-groups" class="nav-groups" :class="{ expanded: navExpanded }">
        <section v-for="group in navGroups" :key="group.title" class="nav-group">
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

      <div class="sidebar-footer">
        <article class="sidebar-note">
          <p>当前焦点</p>
          <strong>{{ pageTitle }}</strong>
          <span>{{ pageGuide || pageDescription }}</span>
        </article>
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

          <div v-if="contextChips.length" class="context-chip-row">
            <span v-for="chip in contextChips" :key="`${chip.label}-${chip.value}`" class="context-chip">
              <small>{{ chip.label }}</small>
              <strong>{{ chip.value }}</strong>
            </span>
          </div>
        </div>

        <div class="banner-pulse">
          <span>当前阶段</span>
          <strong>{{ pageStatusLabel }}</strong>
          <small>{{ contextChips.length > 1 ? `已挂载 ${contextChips.length - 1} 条操作上下文` : '当前页面可直接开始作业' }}</small>
        </div>
      </header>

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

      <main class="page-body">
        <RouterView />
      </main>
    </div>
  </div>
</template>
