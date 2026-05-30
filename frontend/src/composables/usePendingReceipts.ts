import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchPendingReceipts } from '../services/api'
import type { PurchasePendingReceipt } from '../types/inventory'

export function usePendingReceipts() {
  const pendingReceiptsLoading = ref(false)
  const pendingReceipts = ref<PurchasePendingReceipt[]>([])
  const selectedPendingReceiptId = ref<number | null>(null)

  const selectedPendingReceipt = computed(
    () => pendingReceipts.value.find((item) => item.purchase_item_id === selectedPendingReceiptId.value) ?? null,
  )

  function choosePendingReceipt(item: PurchasePendingReceipt | null) {
    selectedPendingReceiptId.value = item?.purchase_item_id ?? null
  }

  async function loadPendingReceipts() {
    pendingReceiptsLoading.value = true
    try {
      pendingReceipts.value = await fetchPendingReceipts()

      if (selectedPendingReceiptId.value) {
        const existing = pendingReceipts.value.find((item) => item.purchase_item_id === selectedPendingReceiptId.value)
        if (!existing) {
          selectedPendingReceiptId.value = null
        }
      }
    } catch {
      pendingReceipts.value = []
      ElMessage.error('待收货采购列表加载失败。')
    } finally {
      pendingReceiptsLoading.value = false
    }
  }

  return {
    choosePendingReceipt,
    loadPendingReceipts,
    pendingReceipts,
    pendingReceiptsLoading,
    selectedPendingReceipt,
    selectedPendingReceiptId,
  }
}
