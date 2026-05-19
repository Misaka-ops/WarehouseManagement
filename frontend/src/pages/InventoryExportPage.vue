<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { exportInventoryWorkbook } from '../services/api'

const { dashboard, loadDashboard } = useInventoryWorkspace()

const exporting = ref(false)
const lastDownloadedFile = ref<string | null>(null)

async function downloadWorkbook() {
  exporting.value = true
  try {
    const { blob, filename } = await exportInventoryWorkbook()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)

    lastDownloadedFile.value = filename
    ElMessage.success('库存 Excel 已开始导出。')
  } catch (error) {
    const message = error instanceof Error ? error.message : '库存导出失败'
    ElMessage.error(message)
  } finally {
    exporting.value = false
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
          <p class="section-kicker">仓库模板导出</p>
          <h3>把当前库存导出成原格式 Excel</h3>
        </div>
        <span class="section-meta">沿用 `原物料库存清单` 原模板结构</span>
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
        <article class="metric-card danger">
          <span>低库存</span>
          <strong>{{ dashboard?.summary.low_stock_items ?? '--' }}</strong>
        </article>
      </div>
    </section>

    <div class="content-grid">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">下载文件</p>
            <h3>导出仓库 Excel</h3>
          </div>
          <span class="section-meta">{{ lastDownloadedFile || '尚未导出' }}</span>
        </div>

        <div class="import-panel">
          <div class="upload-dropzone static-card">
            <span class="upload-kicker">Excel Export</span>
            <strong>下载当前库存快照</strong>
            <p>生成当前库存 Excel 文件。</p>
          </div>

          <div class="link-row">
            <button class="primary-button" :disabled="exporting" type="button" @click="downloadWorkbook">
              {{ exporting ? '导出中...' : '下载原格式库存 Excel' }}
            </button>
            <RouterLink class="action-link ghost" to="/overview">返回仓库总览</RouterLink>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>
