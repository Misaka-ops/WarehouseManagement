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
const pageDescription = computed(
  () => String(route.meta.description ?? '把日常收发、库存巡检和采购收货拆成清晰的独立工作流。'),
)
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar-shell">
      <div class="brand-panel">
        <p class="eyebrow">Warehouse Flow</p>
        <h1>仓储运营台</h1>
        <p>主页回到工作台，再从这里进入仓库总览、入库、出库和采购收货。</p>
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

      <div class="sidebar-footer">
        <div class="sidebar-note">
          <p>数据源</p>
          <strong>Excel 初始化 + 本地 SQLite 实时读写</strong>
          <span>库存数据来自后端接口，入库/出库会直接更新数据库。</span>
        </div>
      </div>
    </aside>

    <div class="page-shell">
      <header class="page-banner">
        <div>
          <p class="eyebrow">{{ pageEyebrow }}</p>
          <h2>{{ pageTitle }}</h2>
          <p>{{ pageDescription }}</p>
        </div>

        <div class="banner-pulse">
          <span>操作路径</span>
          <strong>工作台 / 功能页面分离</strong>
        </div>
      </header>

      <main class="page-body">
        <RouterView />
      </main>
    </div>
  </div>
</template>
