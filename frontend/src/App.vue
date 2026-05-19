<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

type NavItem = {
  to: string
  label: string
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
      { to: '/', label: '工作台' },
      { to: '/overview', label: '仓库总览' },
    ],
  },
  {
    title: '执行',
    items: [
      { to: '/receipt', label: '入库' },
      { to: '/issue', label: '出库' },
      { to: '/purchase-import', label: '采购导入' },
      { to: '/purchase-receiving', label: '采购收货' },
      { to: '/inventory-import', label: '库存导入' },
      { to: '/inventory-export', label: '库存导出' },
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
