<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { usePendingReceipts } from '../composables/usePendingReceipts'
import {
  fetchPurchaseImportStates,
  importFeishuPurchase,
  importPurchaseWorkbook,
  previewFeishuPurchase,
  updateImportedPurchaseItems,
  updatePurchaseImportStates,
} from '../services/api'
import type {
  FeishuPurchaseImportResponse,
  FeishuPurchasePreviewOrder,
  FeishuPurchasePreviewResponse,
  PurchaseImportItem,
  PurchaseImportResponse,
  PurchaseImportState,
} from '../types/inventory'

type EditableImportItem = PurchaseImportItem & {
  requested_quantity_input: number | null
}

const { dashboard, inventoryItems, loadDashboard } = useInventoryWorkspace()
const { loadPendingReceipts } = usePendingReceipts()

const states = ref<PurchaseImportState[]>([])
const selectedFile = ref<File | null>(null)
const importing = ref(false)
const syncingFeishu = ref(false)
const savingStates = ref(false)
const savingAdjustments = ref(false)
const feishuTimeRangeDays = ref(10)
const importResult = ref<PurchaseImportResponse | null>(null)
const feishuSyncResult = ref<FeishuPurchaseImportResponse | null>(null)
const feishuPreviewResult = ref<FeishuPurchasePreviewResponse | null>(null)
const resultDialogVisible = ref(false)
const feishuPreviewDialogVisible = ref(false)
const confirmingFeishuImport = ref(false)
const editableItems = ref<EditableImportItem[]>([])
const selectedFeishuInstanceCodes = ref<string[]>([])

const feishuTimeRangeOptions = [
  { label: '近一天', value: 1 },
  { label: '近五天', value: 5 },
  { label: '近十天', value: 10 },
]

const rowInputs = reactive<Record<string, number>>({})

const unmatchedCount = computed(() => editableItems.value.filter((item) => item.inventory_item_id == null).length)
const fileLabel = computed(() => selectedFile.value?.name ?? '尚未选择采购 Excel 文件')
const feishuPreviewOrders = computed(() => feishuPreviewResult.value?.orders ?? [])
const latestImportedPurchaseItemIds = computed(() =>
  importResult.value?.imported_items.map((item) => item.purchase_item_id).join(',') ?? '',
)
const latestReceivingRouteQuery = computed(() =>
  latestImportedPurchaseItemIds.value
    ? { source: 'purchase-import', purchaseItemIds: latestImportedPurchaseItemIds.value }
    : { source: 'purchase-import' },
)
const importableFeishuOrders = computed(() => feishuPreviewOrders.value.filter((order) => order.can_import))
const importableFeishuInstanceCodes = computed(() => importableFeishuOrders.value.map((order) => order.instance_code))
const selectedFeishuOrders = computed(() =>
  feishuPreviewOrders.value.filter((order) => selectedFeishuInstanceCodes.value.includes(order.instance_code)),
)
const selectedFeishuItemCount = computed(() =>
  selectedFeishuOrders.value.reduce((total, order) => total + order.items.length, 0),
)
const allImportableFeishuSelected = computed(
  () =>
    importableFeishuInstanceCodes.value.length > 0 &&
    selectedFeishuInstanceCodes.value.length === importableFeishuInstanceCodes.value.length,
)

function getErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    const message = error.response?.data?.message
    if (typeof message === 'string' && message.trim()) {
      return message
    }
    return error.message || fallback
  }

  return error instanceof Error ? error.message : fallback
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '未记录'
  }

  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString('zh-CN', { hour12: false })
}

function formatDate(value: string | null) {
  if (!value) {
    return '未记录'
  }

  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString('zh-CN')
}

function formatInventoryOptionLabel(item: {
  material_name: string
  specification: string | null
  unit: string | null
  supplier_name: string | null
  location_name: string | null
}) {
  return [
    item.material_name,
    item.specification || '未填规格',
    `单位 ${item.unit || '未填'}`,
    `供应商 ${item.supplier_name || '未填'}`,
    `区位 ${item.location_name || '未填'}`,
  ].join(' / ')
}

function syncStates(nextStates: PurchaseImportState[]) {
  states.value = nextStates
  for (const state of nextStates) {
    rowInputs[state.sheet_name] = state.last_imported_row
  }
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null
  selectedFile.value = target?.files?.[0] ?? null
}

async function loadImportStates() {
  syncStates(await fetchPurchaseImportStates())
}

async function saveRowStates() {
  savingStates.value = true
  try {
    const nextStates = await updatePurchaseImportStates(
      states.value.map((state) => ({
        sheet_name: state.sheet_name,
        last_imported_row: Number(rowInputs[state.sheet_name] ?? state.last_imported_row),
      })),
    )
    syncStates(nextStates)
    ElMessage.success('采购导入行号已更新。')
  } catch (error) {
    const message = error instanceof Error ? error.message : '保存导入行号失败'
    ElMessage.error(message)
  } finally {
    savingStates.value = false
  }
}

function buildEditableItems(items: PurchaseImportItem[]) {
  editableItems.value = items.map((item) => ({
    ...item,
    requested_quantity_input: item.requested_quantity == null ? null : Number(item.requested_quantity),
  }))
}

function selectFeishuPreviewOrders(orders: FeishuPurchasePreviewOrder[]) {
  selectedFeishuInstanceCodes.value = orders.filter((order) => order.can_import).map((order) => order.instance_code)
}

function toggleFeishuOrderSelection(instanceCode: string) {
  if (selectedFeishuInstanceCodes.value.includes(instanceCode)) {
    selectedFeishuInstanceCodes.value = selectedFeishuInstanceCodes.value.filter((code) => code !== instanceCode)
    return
  }

  selectedFeishuInstanceCodes.value = [...selectedFeishuInstanceCodes.value, instanceCode]
}

function toggleSelectAllFeishuOrders() {
  if (allImportableFeishuSelected.value) {
    selectedFeishuInstanceCodes.value = []
    return
  }

  selectedFeishuInstanceCodes.value = [...importableFeishuInstanceCodes.value]
}

async function submitImport() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择采购 Excel 文件。')
    return
  }

  importing.value = true
  try {
    const response = await importPurchaseWorkbook(selectedFile.value)
    importResult.value = response
    syncStates(response.updated_states)
    buildEditableItems(response.imported_items)
    await loadDashboard({ quiet: true })

    if (response.imported_item_count > 0) {
      resultDialogVisible.value = true
      ElMessage.success(`本次导入 ${response.imported_item_count} 条采购明细。`)
    } else {
      ElMessage.success('本次没有检测到新的采购行。')
    }

    if (response.warnings.length) {
      response.warnings.forEach((warning) => ElMessage.warning(warning))
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '采购导入失败'
    ElMessage.error(message)
  } finally {
    importing.value = false
  }
}

async function syncFeishuImport() {
  syncingFeishu.value = true
  try {
    const response = await previewFeishuPurchase({ time_range_days: feishuTimeRangeDays.value })
    feishuPreviewResult.value = response
    selectFeishuPreviewOrders(response.orders)

    if (!response.orders.length) {
      ElMessage.success(`抓取 ${response.fetched_instance_count} 条实例，本次没有获取到可展示的飞书采购数据。`)
      return
    }

    feishuPreviewDialogVisible.value = true
    if (response.warnings.length) {
      ElMessage.warning(
        `抓取 ${response.fetched_instance_count} 条实例，可导入 ${response.importable_instance_count} 单 / ${response.importable_item_count} 条物品，但有 ${response.warnings.length} 条警告。`,
      )
    } else {
      ElMessage.success(
        `抓取 ${response.fetched_instance_count} 条实例，可导入 ${response.importable_instance_count} 单 / ${response.importable_item_count} 条物品，请确认后再加入采购收货。`,
      )
    }
  } catch (error) {
    const message = getErrorMessage(error, '飞书采购同步失败')
    ElMessage.error(message)
  } finally {
    syncingFeishu.value = false
  }
}

async function confirmFeishuImport() {
  if (!selectedFeishuInstanceCodes.value.length) {
    ElMessage.warning('请先勾选要加入采购收货的飞书采购单。')
    return
  }

  confirmingFeishuImport.value = true
  try {
    const response = await importFeishuPurchase({
      approval_code: feishuPreviewResult.value?.approval_code,
      instance_codes: selectedFeishuInstanceCodes.value,
    })
    feishuSyncResult.value = response
    feishuPreviewDialogVisible.value = false
    await Promise.all([loadDashboard({ quiet: true }), loadPendingReceipts()])

    if (response.warnings.length) {
      ElMessage.warning(`已确认导入，但有 ${response.warnings.length} 条警告，请留意下方结果。`)
    }

    if (response.reimported_order_count > 0) {
      ElMessage.success(`已导入 ${response.reimported_order_count} 单 / ${response.reimported_item_count} 条飞书采购明细。`)
    } else if (response.imported_order_count > 0) {
      ElMessage.success(`已导入 ${response.imported_order_count} 单 / ${response.imported_item_count} 条飞书采购明细。`)
    } else {
      ElMessage.success('本次确认后没有新增可导入的飞书采购单。')
    }
  } catch (error) {
    const message = getErrorMessage(error, '确认导入飞书采购失败')
    ElMessage.error(message)
  } finally {
    confirmingFeishuImport.value = false
  }
}

async function saveImportedAdjustments() {
  if (!editableItems.value.length) {
    return
  }

  savingAdjustments.value = true
  try {
    const response = await updateImportedPurchaseItems(
      editableItems.value.map((item) => ({
        purchase_item_id: item.purchase_item_id,
        material_name: item.material_name,
        specification: item.specification,
        requested_quantity: item.requested_quantity_input,
        unit: item.unit,
        expected_arrival: item.expected_arrival,
        inventory_item_id: item.inventory_item_id,
      })),
    )
    buildEditableItems(response.items)
    ElMessage.success(`已保存 ${response.updated_item_count} 条导入调整。`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '保存导入调整失败'
    ElMessage.error(message)
  } finally {
    savingAdjustments.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadDashboard(), loadImportStates()])
})
</script>

<template>
  <div class="page-stack">
    <section class="page-section hero-section purchase-import-task-page">
      <div class="section-heading">
        <div>
          <p class="section-kicker">采购导入</p>
          <h3>确认行号后，直接选择本次导入入口</h3>
        </div>
        <span class="section-meta">单主流程</span>
      </div>

      <p class="section-copy tight">系统会按每个工作表上次导入行号继续增量读取。需要重跑时，只改行号，再从 Excel 或飞书进入本次导入。</p>

      <div class="metric-grid compact">
        <article class="metric-card accent">
          <span>待处理采购</span>
          <strong>{{ dashboard?.summary.pending_purchase_orders ?? '--' }}</strong>
        </article>
        <article class="metric-card">
          <span>当前库存项目</span>
          <strong>{{ dashboard?.summary.total_items ?? '--' }}</strong>
        </article>
      </div>
    </section>

    <div class="content-grid">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">步骤 1</p>
            <h3>确认行号</h3>
          </div>
          <span class="section-meta">支持手工修正</span>
        </div>

        <p class="section-copy tight">下次导入会从这些行号之后开始读取；要回退范围，先改这里。</p>

        <div class="import-notes">
          <article v-for="state in states" :key="state.sheet_name" class="note-card">
            <strong>{{ state.sheet_name }}</strong>
            <p>表头行：{{ state.header_row }}</p>
            <p>上次导入文件：{{ state.last_workbook_name || '未记录' }}</p>
            <label class="field compact-field">
              <span>上次导入到的 Excel 行号</span>
              <input v-model.number="rowInputs[state.sheet_name]" min="0" step="1" type="number" inputmode="numeric" />
            </label>
          </article>
        </div>

        <div class="link-row">
          <button class="primary-button" :disabled="savingStates" type="button" @click="saveRowStates">
            {{ savingStates ? '保存中...' : '保存导入行号' }}
          </button>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">步骤 2</p>
            <h3>选择本次导入入口</h3>
          </div>
          <span class="section-meta">Excel / 飞书并列入口</span>
        </div>

        <p class="section-copy tight">两个入口都会沿用当前行号范围。Excel 适合本地采购表，飞书会先拉预览再确认导入。</p>

        <div class="content-grid">
          <div class="import-panel">
            <label class="upload-dropzone">
              <input accept=".xlsx,.xlsm,.xltx,.xltm" class="upload-input" type="file" @change="handleFileChange" />
              <span class="upload-kicker">Excel Import</span>
              <strong>{{ fileLabel }}</strong>
              <p>上传后只读取当前行号之后的新采购行。</p>
            </label>

            <div class="selection-toolbar selection-toolbar-inline">
              <div class="selection-status">
                <span>本地导入</span>
                <strong>按当前增量范围读取采购 Excel</strong>
                <small>支持 `Sheet1` 和 `佳时坤`。</small>
              </div>
            </div>

            <div class="link-row">
              <button class="primary-button" :disabled="importing || !selectedFile" type="button" @click="submitImport">
                {{ importing ? '导入中...' : '开始采购增量导入' }}
              </button>
            </div>
          </div>

          <div class="import-panel">
            <article class="note-card warm-note">
              <strong>飞书采购同步</strong>
              <p>先抓取审批实例并预览物品，再确认哪些采购单加入待收货。</p>
              <label class="field compact-field">
                <span>同步范围</span>
                <select v-model.number="feishuTimeRangeDays">
                  <option v-for="option in feishuTimeRangeOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>
            </article>

            <div class="selection-toolbar selection-toolbar-inline">
              <div class="selection-status">
                <span>飞书入口</span>
                <strong>预览后再确认导入采购收货</strong>
                <small>会保留不可导入实例并给出原因。</small>
              </div>
            </div>

            <div class="link-row">
              <button class="action-link secondary" :disabled="syncingFeishu" type="button" @click="syncFeishuImport">
                {{ syncingFeishu ? '同步中...' : '同步并预览飞书采购申请' }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section v-if="importResult || feishuSyncResult" class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">步骤 3</p>
          <h3>最近结果与后续动作</h3>
        </div>
        <span class="section-meta">
          {{ importResult ? `未匹配库存项：${importResult.unmatched_item_count}` : `审批编码：${feishuSyncResult?.approval_code}` }}
        </span>
      </div>

      <div class="metric-grid compact">
        <template v-if="importResult">
          <article class="metric-card">
            <span>导入采购单</span>
            <strong>{{ importResult.imported_order_count }}</strong>
          </article>
          <article class="metric-card">
            <span>导入采购明细</span>
            <strong>{{ importResult.imported_item_count }}</strong>
          </article>
          <article class="metric-card danger">
            <span>未匹配库存项</span>
            <strong>{{ importResult.unmatched_item_count }}</strong>
          </article>
        </template>
        <template v-else>
          <article class="metric-card">
            <span>导入采购单</span>
            <strong>{{ feishuSyncResult?.imported_order_count ?? 0 }}</strong>
          </article>
          <article class="metric-card">
            <span>导入采购明细</span>
            <strong>{{ feishuSyncResult?.imported_item_count ?? 0 }}</strong>
          </article>
          <article class="metric-card accent">
            <span>抓取实例</span>
            <strong>{{ feishuSyncResult?.fetched_instance_count ?? 0 }}</strong>
          </article>
        </template>
      </div>

      <div class="selection-toolbar business-toolbar import-context-toolbar">
        <div class="selection-status">
          <span>下一步</span>
          <strong>{{ importResult ? '带着本次导入范围进入采购收货' : '继续转入采购收货核对待收货' }}</strong>
          <small v-if="importResult">进入后默认只看这次导入的 {{ importResult.imported_item_count }} 条待收货，避免在全部列表里重新查找。</small>
          <small v-else>飞书采购已经转入待收货后，可以继续回采购收货完成核对与入库。</small>
        </div>

        <div class="selection-actions">
          <RouterLink class="action-link" :to="{ path: '/purchase-receiving', query: latestReceivingRouteQuery }">
            {{ importResult?.imported_items?.length ? '处理本次导入待收货' : '去看采购收货' }}
          </RouterLink>
          <button v-if="importResult" class="action-link ghost" type="button" @click="resultDialogVisible = true">查看并调整导入明细</button>
        </div>
      </div>

      <div v-if="feishuSyncResult" class="import-notes compact-notes">
        <article class="note-card">
          <strong>{{ feishuSyncResult.sync_state.last_sync_status || '同步已完成' }}</strong>
          <p>{{ feishuSyncResult.sync_state.last_sync_message || '飞书审批实例已同步到本地。' }}</p>
          <p>最近同步：{{ formatDateTime(feishuSyncResult.sync_state.last_synced_at) }}</p>
        </article>
        <article v-for="(warning, index) in feishuSyncResult.warnings" :key="`${warning}-${index}`" class="note-card warm-note">
          <strong>警告</strong>
          <p>{{ warning }}</p>
        </article>
      </div>
    </section>

    <section v-if="importResult?.imported_items?.length" class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">最近导入明细</p>
          <h3>导入清单</h3>
        </div>
        <span class="section-meta">{{ importResult.imported_item_count }} 条</span>
      </div>

      <div class="console-table">
        <div class="console-table-scroll">
          <div class="console-table-header import-table-grid">
            <span class="console-header-cell">物料</span>
            <span class="console-header-cell">规格</span>
            <span class="console-header-cell">供应商</span>
            <span class="console-header-cell">项目</span>
            <span class="console-header-cell">来源</span>
            <span class="console-header-cell">数量</span>
            <span class="console-header-cell">对齐状态</span>
            <span class="console-header-cell">操作</span>
          </div>

          <article v-for="item in importResult.imported_items" :key="item.purchase_item_id" class="console-table-row import-table-grid">
            <div class="console-cell">
              <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
            </div>
            <div class="console-cell muted console-clamp-2" :title="item.specification || '未填'">{{ item.specification || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填'">{{ item.supplier_name || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="item.project_name || '未填'">{{ item.project_name || '未填' }}</div>
            <div class="console-cell muted console-clamp-2" :title="`${item.sheet_name} / 第 ${item.source_row_number} 行`">{{ item.sheet_name }} / 第 {{ item.source_row_number }} 行</div>
            <div class="console-cell">
              <span class="console-badge info">{{ item.requested_quantity || '--' }} {{ item.unit || '件' }}</span>
            </div>
            <div class="console-cell">
              <span :class="['console-badge', item.inventory_item_id ? 'ok' : 'warn']">
                {{ item.inventory_item_id ? '已匹配' : '待匹配' }}
              </span>
            </div>
            <div class="console-row-actions">
              <button class="console-action ghost" type="button" @click="resultDialogVisible = true">编辑</button>
              <RouterLink
                class="console-action secondary"
                :to="{
                  path: '/purchase-receiving',
                  query: {
                    source: 'purchase-import',
                    purchaseItemId: item.purchase_item_id,
                    purchaseItemIds: latestImportedPurchaseItemIds,
                  },
                }"
              >
                去收货
              </RouterLink>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section v-if="feishuSyncResult" class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">飞书同步结果</p>
          <h3>{{ feishuSyncResult.sync_state.last_sync_status || '同步已完成' }}</h3>
        </div>
        <span class="section-meta">审批编码：{{ feishuSyncResult.approval_code }}</span>
      </div>

      <p class="section-copy">
        {{ feishuSyncResult.sync_state.last_sync_message || '飞书审批实例已同步到本地。' }}
      </p>

      <div class="metric-grid compact">
        <article class="metric-card">
          <span>抓取实例</span>
          <strong>{{ feishuSyncResult.fetched_instance_count }}</strong>
        </article>
        <article class="metric-card">
          <span>新增实例</span>
          <strong>{{ feishuSyncResult.created_instance_count }}</strong>
        </article>
        <article class="metric-card">
          <span>更新实例</span>
          <strong>{{ feishuSyncResult.updated_instance_count }}</strong>
        </article>
        <article class="metric-card accent">
          <span>跳过实例</span>
          <strong>{{ feishuSyncResult.skipped_instance_count }}</strong>
        </article>
        <article class="metric-card">
          <span>导入采购单</span>
          <strong>{{ feishuSyncResult.imported_order_count }}</strong>
        </article>
        <article class="metric-card">
          <span>导入明细</span>
          <strong>{{ feishuSyncResult.imported_item_count }}</strong>
        </article>
      </div>

      <div class="import-notes compact-notes">
        <article class="note-card">
          <strong>最近同步</strong>
          <p>同步时间：{{ formatDateTime(feishuSyncResult.sync_state.last_synced_at) }}</p>
          <p>最后实例：{{ feishuSyncResult.sync_state.last_synced_instance_code || '未记录' }}</p>
        </article>
        <article v-for="(warning, index) in feishuSyncResult.warnings" :key="`${warning}-${index}`" class="note-card warm-note">
          <strong>警告</strong>
          <p>{{ warning }}</p>
        </article>
      </div>
    </section>

    <el-dialog v-model="feishuPreviewDialogVisible" title="确认加入采购收货的飞书物品" width="92%">
      <div class="dialog-summary">
        <span>抓取实例：{{ feishuPreviewResult?.fetched_instance_count ?? 0 }} 条</span>
        <span>可导入实例：{{ feishuPreviewResult?.importable_instance_count ?? 0 }} 条</span>
      </div>

      <div class="dialog-summary preview-selection-summary">
        <span>已勾选采购单：{{ selectedFeishuInstanceCodes.length }} 条</span>
        <span>已勾选物品：{{ selectedFeishuItemCount }} 条</span>
      </div>

      <div class="selection-toolbar preview-toolbar">
        <label class="checkbox-chip">
          <input :checked="allImportableFeishuSelected" type="checkbox" @change="toggleSelectAllFeishuOrders" />
          <span>全选当前可导入采购单</span>
        </label>
        <span v-if="feishuPreviewOrders.some((order) => !order.can_import)" class="section-meta">
          不可导入的实例会保留展示，并显示原因。
        </span>
      </div>

      <div class="stack-list feishu-preview-list">
        <article
          v-for="order in feishuPreviewOrders"
          :key="order.instance_code"
          class="data-row clickable triplet preview-order-card"
          :class="{ active: selectedFeishuInstanceCodes.includes(order.instance_code), disabled: !order.can_import }"
          @click="order.can_import ? toggleFeishuOrderSelection(order.instance_code) : undefined"
        >
          <div class="row-checkbox" @click.stop>
            <input
              :checked="selectedFeishuInstanceCodes.includes(order.instance_code)"
              :disabled="!order.can_import"
              type="checkbox"
              @change="toggleFeishuOrderSelection(order.instance_code)"
            />
          </div>

          <div class="data-row-main">
            <div class="data-row-head">
              <strong>{{ order.requester || order.creator_name || order.title || '未命名飞书采购单' }}</strong>
              <div class="preview-order-badges">
                <span :class="['console-badge', order.can_import ? 'ok' : 'warn']">
                  {{ order.can_import ? '待确认导入' : order.skip_reason || '不可导入' }}
                </span>
                <span class="console-badge info">{{ order.items.length }} 条物品</span>
              </div>
            </div>

            <div class="data-row-meta">
              <span>实例号：{{ order.instance_code }}</span>
              <span>流水号：{{ order.serial_number || '未记录' }}</span>
              <span>项目：{{ order.project_name || '未填' }}</span>
              <span>类别：{{ order.purchase_category || '未填' }}</span>
              <span>请购日期：{{ formatDate(order.requested_at) }}</span>
              <span>审批状态：{{ order.status || '未记录' }}</span>
            </div>

            <div class="preview-item-list">
              <div v-for="item in order.items" :key="`${order.instance_code}-${item.line_no}`" class="preview-item-row">
                <div class="preview-item-main">
                  <strong>{{ item.material_name }}</strong>
                  <span>{{ item.specification || '未填规格' }}</span>
                </div>
                <div class="preview-item-meta">
                  <span>数量：{{ item.requested_quantity || '--' }} {{ item.unit || '件' }}</span>
                  <span>金额：{{ item.total_amount || '--' }}</span>
                  <span>{{ item.inventory_item_id ? '已匹配库存项' : '未匹配库存项' }}</span>
                </div>
              </div>
            </div>
          </div>
        </article>

        <div v-if="!feishuPreviewOrders.length" class="empty-state">本次没有可展示的飞书采购明细。</div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="action-link ghost" type="button" @click="feishuPreviewDialogVisible = false">先不导入</button>
          <button
            class="primary-button"
            :disabled="confirmingFeishuImport || !selectedFeishuInstanceCodes.length"
            type="button"
            @click="confirmFeishuImport"
          >
            {{ confirmingFeishuImport ? '导入中...' : `确认加入采购收货（${selectedFeishuItemCount} 条物品）` }}
          </button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="resultDialogVisible" title="本次采购导入清单" width="90%">
      <div class="dialog-summary">
        <span>导入明细：{{ editableItems.length }} 条</span>
        <span>待手工对齐库存项：{{ unmatchedCount }} 条</span>
      </div>

      <div class="editable-grid-header">
        <span>工作表 / 行号</span>
        <span>供应商</span>
        <span>物料名称</span>
        <span>规格型号</span>
        <span>数量</span>
        <span>单位</span>
        <span>到货日期</span>
        <span>匹配库存项</span>
      </div>

      <div class="editable-grid">
        <div v-for="item in editableItems" :key="item.purchase_item_id" class="editable-grid-row">
          <span class="cell meta">{{ item.sheet_name }} / 第 {{ item.source_row_number }} 行</span>
          <span class="cell meta">{{ item.supplier_name || '未填' }}</span>
          <input v-model="item.material_name" class="cell-input" type="text" />
          <input v-model="item.specification" class="cell-input" type="text" />
          <input v-model.number="item.requested_quantity_input" class="cell-input" min="0" step="0.01" type="number" />
          <input v-model="item.unit" class="cell-input" type="text" />
          <input v-model="item.expected_arrival" class="cell-input" type="date" />
          <select v-model="item.inventory_item_id" class="cell-input">
            <option :value="null">未匹配 / 留空</option>
            <option v-for="inventoryItem in inventoryItems" :key="inventoryItem.id" :value="inventoryItem.id">
              {{ formatInventoryOptionLabel(inventoryItem) }}
            </option>
          </select>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="action-link ghost" type="button" @click="resultDialogVisible = false">先关闭</button>
          <button class="primary-button" :disabled="savingAdjustments || !editableItems.length" type="button" @click="saveImportedAdjustments">
            {{ savingAdjustments ? '保存中...' : '保存本次导入调整' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
