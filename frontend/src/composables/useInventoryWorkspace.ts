import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchDashboard, fetchItemTransactions } from '../services/api'
import type { DashboardResponse, InventoryItem, InventoryTransaction } from '../types/inventory'

export function useInventoryWorkspace() {
  const loading = ref(true)
  const historyLoading = ref(false)
  const dashboard = ref<DashboardResponse | null>(null)
  const itemTransactions = ref<InventoryTransaction[]>([])
  const selectedItemId = ref<number | null>(null)

  const inventoryItems = computed(() => dashboard.value?.items ?? [])
  const selectedItem = computed(() => inventoryItems.value.find((item) => item.id === selectedItemId.value) ?? null)

  function selectItem(item: InventoryItem) {
    selectedItemId.value = item.id
  }

  async function loadDashboard(options: { quiet?: boolean } = {}) {
    if (!options.quiet) {
      loading.value = true
    }

    try {
      dashboard.value = await fetchDashboard()

      if (selectedItemId.value) {
        const existing = dashboard.value.items.find((item) => item.id === selectedItemId.value)
        if (!existing) {
          selectedItemId.value = null
        }
      }

      if (!selectedItemId.value) {
        const firstItem = dashboard.value.items[0]
        if (firstItem) {
          selectedItemId.value = firstItem.id
        }
      }
    } catch {
      ElMessage.error('库存数据加载失败，请确认后端服务已启动。')
    } finally {
      if (!options.quiet) {
        loading.value = false
      }
    }
  }

  async function loadTransactions(itemId: number) {
    historyLoading.value = true
    try {
      itemTransactions.value = await fetchItemTransactions(itemId)
    } catch {
      itemTransactions.value = []
      ElMessage.error('当前物料流水加载失败。')
    } finally {
      historyLoading.value = false
    }
  }

  watch(selectedItemId, async (itemId) => {
    if (itemId) {
      await loadTransactions(itemId)
    } else {
      itemTransactions.value = []
    }
  })

  return {
    dashboard,
    historyLoading,
    inventoryItems,
    itemTransactions,
    loading,
    loadDashboard,
    loadTransactions,
    selectItem,
    selectedItem,
    selectedItemId,
  }
}
