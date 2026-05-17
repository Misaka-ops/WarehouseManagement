<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import {
  fetchPurchaseImportStates,
  importPurchaseWorkbook,
  updateImportedPurchaseItems,
  updatePurchaseImportStates,
} from '../services/api'
import type { PurchaseImportItem, PurchaseImportResponse, PurchaseImportState } from '../types/inventory'

type EditableImportItem = PurchaseImportItem & {
  requested_quantity_input: number | null
}

const { dashboard, inventoryItems, loadDashboard } = useInventoryWorkspace()

const states = ref<PurchaseImportState[]>([])
const selectedFile = ref<File | null>(null)
const importing = ref(false)
const savingStates = ref(false)
const savingAdjustments = ref(false)
const importResult = ref<PurchaseImportResponse | null>(null)
const resultDialogVisible = ref(false)
const editableItems = ref<EditableImportItem[]>([])

const rowInputs = reactive<Record<string, number>>({})

const unmatchedCount = computed(() => editableItems.value.filter((item) => item.inventory_item_id == null).length)
const fileLabel = computed(() => selectedFile.value?.name ?? '尚未选择采购 Excel 文件')

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
    <section class="page-section hero-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">采购增量导入</p>
          <h3>按上次行号之后的内容导入采购清单</h3>
        </div>
        <span class="section-meta">支持本地上传采购 Excel，并记录每个工作表的最新导入行号</span>
      </div>

      <p class="section-copy">
        当前导入策略是增量导入。系统会记住每个采购工作表上次导入到哪一行，下次只导入后续新增内容；如果你需要回退或重跑，也可以手工修改这个行号。
      </p>

      <div class="metric-grid compact">
        <article class="metric-card">
          <span>当前库存项目</span>
          <strong>{{ dashboard?.summary.total_items ?? '--' }}</strong>
        </article>
        <article class="metric-card accent">
          <span>待处理采购</span>
          <strong>{{ dashboard?.summary.pending_purchase_orders ?? '--' }}</strong>
        </article>
      </div>
    </section>

    <div class="content-grid">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">导入状态</p>
            <h3>先确认每个工作表的行号</h3>
          </div>
          <span class="section-meta">用户可手工修改</span>
        </div>

        <div class="import-notes">
          <article v-for="state in states" :key="state.sheet_name" class="note-card">
            <strong>{{ state.sheet_name }}</strong>
            <p>表头行：{{ state.header_row }}</p>
            <p>上次导入文件：{{ state.last_workbook_name || '未记录' }}</p>
            <label class="field compact-field">
              <span>上次导入到的 Excel 行号</span>
              <input v-model.number="rowInputs[state.sheet_name]" min="0" step="1" type="number" />
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
            <p class="section-kicker">上传采购表单</p>
            <h3>执行本次增量导入</h3>
          </div>
          <span class="section-meta">支持 `Sheet1` 和 `佳时坤`</span>
        </div>

        <div class="import-panel">
          <label class="upload-dropzone">
            <input accept=".xlsx,.xlsm,.xltx,.xltm" class="upload-input" type="file" @change="handleFileChange" />
            <span class="upload-kicker">Purchase Upload</span>
            <strong>{{ fileLabel }}</strong>
            <p>上传后会按当前记录的上次导入行号，只导入新增采购行。</p>
          </label>

          <div class="import-notes">
            <article class="note-card">
              <strong>本次可做</strong>
              <p>增量导入、记录并修改导入行号、导入后弹窗查看清单、手工调整物料和库存匹配。</p>
            </article>
            <article class="note-card warm-note">
              <strong>需要你判断的点</strong>
              <p>采购表单与现有库存项目名称或规格不一致时，目前只做精确匹配，再由你在结果弹窗里手工修正。</p>
            </article>
          </div>

          <div class="link-row">
            <button class="primary-button" :disabled="importing || !selectedFile" type="button" @click="submitImport">
              {{ importing ? '导入中...' : '开始采购增量导入' }}
            </button>
            <RouterLink class="action-link ghost" to="/purchase-receiving">去看采购收货</RouterLink>
          </div>
        </div>
      </section>
    </div>

    <section v-if="importResult" class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">最近一次结果</p>
          <h3>{{ importResult.workbook_name }}</h3>
        </div>
        <span class="section-meta">未匹配库存项：{{ importResult.unmatched_item_count }}</span>
      </div>

      <div class="metric-grid compact">
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
      </div>
    </section>

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
              {{ inventoryItem.material_name }} / {{ inventoryItem.specification || '未填规格' }}
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
