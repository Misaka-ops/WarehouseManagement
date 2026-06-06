<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from './composables/useAuth'
import type { InventoryViewKind } from './types/inventory'

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

const route = useRoute()
const router = useRouter()
const { currentUser, isAuthenticated, logout } = useAuth()
const navExpanded = ref(false)
const inventoryViewKind = computed<InventoryViewKind>({
  get: () => (route.path === '/overview' && route.query.kind === 'finished' ? 'finished' : 'raw'),
  set: (nextKind) => {
    void router.push({ path: '/overview', query: { kind: nextKind } })
  },
})
const isFinishedOverview = computed(() => route.path === '/overview' && inventoryViewKind.value === 'finished')

const navGroups: NavGroup[] = [
  {
    title: '工作台',
    items: [{ to: '/', kicker: '总览', label: '工作台', requiresAuth: true }],
  },
  {
    title: '库存查询',
    items: [{ to: '/overview', kicker: '台账', label: '库存查询与台账' }],
  },
  {
    title: '采购流程',
    items: [
      { to: '/purchase-import', kicker: '导入', label: '采购导入与同步', requiresAuth: true },
      { to: '/purchase-receiving', kicker: '收货', label: '采购收货入库', requiresAuth: true },
    ],
  },
  {
    title: '直接作业',
    items: [
      { to: '/receipt', kicker: '入库', label: '直接入库', requiresAuth: true },
      { to: '/issue', kicker: '出库', label: '直接出库', requiresAuth: true },
      { to: '/inventory-manual', kicker: '录入', label: '手动录入库存', requiresAuth: true },
    ],
  },
  {
    title: '数据维护',
    items: [
      { to: '/inventory-import', kicker: '导入', label: '库存导入', requiresAuth: true },
      { to: '/inventory-export', kicker: '导出', label: '库存导出', requiresAuth: true },
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

const pageTitle = computed(() => (isFinishedOverview.value ? '成品库存台账' : String(route.meta.title ?? '仓储控制台')))

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

function isOverviewNavItem(item: NavItem) {
  return item.to === '/overview'
}

function navigateToCurrentOverview() {
  void router.push({ path: '/overview', query: { kind: inventoryViewKind.value } })
}
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar-shell">
      <div class="brand-panel">
        <p class="eyebrow">仓储运营</p>
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
          <template v-for="item in group.items" :key="item.to">
            <div
              v-if="isOverviewNavItem(item)"
              class="nav-link nav-link-select"
              :class="{ active: route.path === item.to }"
              role="button"
              tabindex="0"
              @click="navigateToCurrentOverview"
              @keydown.enter.prevent="navigateToCurrentOverview"
              @keydown.space.prevent="navigateToCurrentOverview"
            >
              <span class="nav-kicker">{{ inventoryViewKind === 'finished' ? '成品' : item.kicker }}</span>
              <strong>{{ inventoryViewKind === 'finished' ? '成品库存台账' : item.label }}</strong>
              <label class="nav-select-shell" @click.stop>
                <span class="nav-select-label">当前查看</span>
                <select v-model="inventoryViewKind">
                  <option value="raw">原料台账</option>
                  <option value="finished">成品台账</option>
                </select>
              </label>
            </div>
            <RouterLink
              v-else
              :to="item.to"
              class="nav-link"
              :class="{ active: route.path === item.to }"
            >
              <span class="nav-kicker">{{ item.kicker }}</span>
              <strong>{{ item.label }}</strong>
            </RouterLink>
          </template>
        </section>
      </div>
    </aside>

    <div class="page-shell">
      <main class="page-body">
        <RouterView />
      </main>
    </div>
  </div>
</template>
