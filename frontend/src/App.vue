<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

type NavItem = {
  to: string
  label: string
  kicker: string
}

type NavGroup = {
  title: string
  items: NavItem[]
}

const route = useRoute()

const navGroups: NavGroup[] = [
  {
    title: '总览',
    items: [
      { to: '/', label: '工作台', kicker: 'Hub' },
      { to: '/overview', label: '仓库总览', kicker: 'Stock' },
    ],
  },
  {
    title: '执行',
    items: [
      { to: '/receipt', label: '入库', kicker: 'Receipt' },
      { to: '/issue', label: '出库', kicker: 'Issue' },
      { to: '/purchase-import', label: '采购导入', kicker: 'PI' },
      { to: '/purchase-receiving', label: '采购收货', kicker: 'PO' },
      { to: '/inventory-import', label: '库存导入', kicker: 'Import' },
      { to: '/inventory-export', label: '库存导出', kicker: 'Export' },
    ],
  },
]

const pageEyebrow = computed(() => String(route.meta.eyebrow ?? 'Warehouse Flow'))
const pageTitle = computed(() => String(route.meta.title ?? '仓储运营台'))
const pageDescription = computed(() => String(route.meta.description ?? ''))
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar-shell">
      <div class="brand-panel">
        <p class="eyebrow">Warehouse Flow</p>
        <h1>仓储运营台</h1>
      </div>

      <div class="nav-groups">
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
    </aside>

    <div class="page-shell">
      <header class="page-banner">
        <div>
          <p class="eyebrow">{{ pageEyebrow }}</p>
          <h2>{{ pageTitle }}</h2>
          <p v-if="pageDescription">{{ pageDescription }}</p>
        </div>
      </header>

      <main class="page-body">
        <RouterView />
      </main>
    </div>
  </div>
</template>
