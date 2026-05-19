<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { importInventoryWorkbook } from '../services/api'
import type { InventoryImportResponse } from '../types/inventory'

const { dashboard, loadDashboard } = useInventoryWorkspace()

const selectedFile = ref<File | null>(null)
const importing = ref(false)
const importResult = ref<InventoryImportResponse | null>(null)

const fileLabel = computed(() => selectedFile.value?.name ?? '尚未选择 Excel 文件')

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null
  selectedFile.value = target?.files?.[0] ?? null
}

async function submitImport() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择仓库 Excel 文件。')
    return
  }

  importing.value = true
  try {
    importResult.value = await importInventoryWorkbook(selectedFile.value)
    await loadDashboard()
    ElMessage.success('库存 Excel 已导入。')
  } catch (error) {
    const message = error instanceof Error ? error.message : '库存导入失败'
    ElMessage.error(message)
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await loadDashboard()
})
</script>

<template>
  <div class="page-stack">
    <section class="page-section hero-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">仓库模板导入</p>
          <h3>从本地上传库存 Excel</h3>
        </div>
        <span class="section-meta">支持当前仓库模板的 `原物料库存清单` 工作表</span>
      </div>

      <div class="metric-grid compact">
        <article class="metric-card">
          <span>当前库存项目</span>
          <strong>{{ dashboard?.summary.total_items ?? '--' }}</strong>
        </article>
        <article class="metric-card">
          <span>当前库存总量</span>
          <strong>{{ dashboard?.summary.total_stock_quantity ?? '--' }}</strong>
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
            <p class="section-kicker">上传文件</p>
            <h3>选择本地仓库 Excel</h3>
          </div>
          <span class="section-meta">推荐使用 `仓库库存2026最新版_备注并入规格型号.xlsx`</span>
        </div>

        <div class="import-panel">
          <label class="upload-dropzone">
            <input accept=".xlsx,.xlsm,.xltx,.xltm" class="upload-input" type="file" @change="handleFileChange" />
            <span class="upload-kicker">Excel Upload</span>
            <strong>{{ fileLabel }}</strong>
            <p>选择并上传仓库 Excel 文件。</p>
          </label>

          <div class="link-row">
            <button class="primary-button" :disabled="importing || !selectedFile" type="button" @click="submitImport">
              {{ importing ? '导入中...' : '开始导入库存 Excel' }}
            </button>
            <RouterLink class="action-link ghost" to="/overview">去看仓库总览</RouterLink>
          </div>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">导入结果</p>
            <h3>{{ importResult ? '最近一次导入已完成' : '等待导入' }}</h3>
          </div>
          <span class="section-meta">{{ importResult?.workbook_name || '尚未执行导入' }}</span>
        </div>

        <div v-if="importResult" class="stat-grid">
          <article class="stat-card">
            <span>替换旧库存项目</span>
            <strong>{{ importResult.replaced_item_count }}</strong>
          </article>
          <article class="stat-card">
            <span>导入新库存项目</span>
            <strong>{{ importResult.imported_item_count }}</strong>
          </article>
          <article class="stat-card">
            <span>导入库存流水</span>
            <strong>{{ importResult.imported_transaction_count }}</strong>
          </article>
          <article class="stat-card">
            <span>重新关联采购明细</span>
            <strong>{{ importResult.relinked_purchase_item_count }}</strong>
          </article>
        </div>

        <div v-else class="empty-state">
          尚未执行导入。
        </div>
      </section>
    </div>
  </div>
</template>
