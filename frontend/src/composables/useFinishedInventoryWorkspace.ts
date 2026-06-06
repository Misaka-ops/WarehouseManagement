import { computed, ref, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

import { fetchFinishedDashboard, fetchFinishedItemTransactions } from '../services/api'
import type { FinishedDashboardResponse, FinishedInventoryItem, FinishedInventoryTransaction } from '../types/inventory'

export function useFinishedInventoryWorkspace() {
  const loading = ref(true)
  const historyLoading = ref(false)
  const dashboard = ref<FinishedDashboardResponse | null>(null)
  const itemTransactions = ref<FinishedInventoryTransaction[]>([])
  const selectedItemId = ref<number | null>(null)

  const inventoryItems = computed(() => dashboard.value?.items ?? [])
  const selectedItem = computed(() => inventoryItems.value.find((item) => item.row_id === selectedItemId.value) ?? null)

  function selectItem(item: FinishedInventoryItem) {
    selectedItemId.value = item.row_id
  }

  function resolveFinishedInventoryErrorMessage(error: unknown, fallback: string) {
    if (!axios.isAxiosError(error)) {
      return error instanceof Error ? error.message : fallback
    }

    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      if (error.response?.status === 404) {
        return '成品台账接口未就绪，请重启后端服务后再试。'
      }
      if (error.response?.status === 500 && detail.includes('成品库存清单')) {
        return '仓库模板中缺少“成品库存清单”sheet。'
      }
      return detail
    }

    if (error.response?.status === 404) {
      return '成品台账接口未就绪，请重启后端服务后再试。'
    }

    return error.message || fallback
  }

  async function loadDashboard(options: { quiet?: boolean } = {}) {
    if (!options.quiet) {
      loading.value = true
    }

    try {
      dashboard.value = await fetchFinishedDashboard()

      if (selectedItemId.value) {
        const existing = dashboard.value.items.find((item) => item.row_id === selectedItemId.value)
        if (!existing) {
          selectedItemId.value = null
        }
      }
    } catch (error) {
      dashboard.value = null
      itemTransactions.value = []
      const message = resolveFinishedInventoryErrorMessage(error, '成品库存数据加载失败。')
      ElMessage.error(message)
    } finally {
      if (!options.quiet) {
        loading.value = false
      }
    }
  }

  async function loadTransactions(rowId: number) {
    historyLoading.value = true
    try {
      itemTransactions.value = await fetchFinishedItemTransactions(rowId)
    } catch (error) {
      itemTransactions.value = []
      const message = resolveFinishedInventoryErrorMessage(error, '成品派生流水加载失败。')
      ElMessage.error(message)
    } finally {
      historyLoading.value = false
    }
  }

  watch(selectedItemId, async (rowId) => {
    if (rowId) {
      await loadTransactions(rowId)
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
