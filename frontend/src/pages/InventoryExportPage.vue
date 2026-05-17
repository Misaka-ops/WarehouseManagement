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

      <p class="section-copy">
        导出会以当前系统里的库存总览为准，回填到仓库原模板格式 Excel 中。现有库存数量、供应商、区位、最近收发流水会尽量映射回模板列。
      </p>

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
            <p>点击后会生成一个与仓库模板结构一致的 Excel 文件，适合继续交给线下仓库表使用。</p>
          </div>

          <div class="import-notes">
            <article class="note-card">
              <strong>导出内容</strong>
              <p>库存总览中的物料、规格、供应商、库存数量、区位、备注会写回原模板列。</p>
            </article>
            <article class="note-card">
              <strong>流水映射</strong>
              <p>最近入库会写入入库日期和入库数量，最近 3 次出库会依次回填出库槽位。</p>
            </article>
          </div>

          <div class="link-row">
            <button class="primary-button" :disabled="exporting" type="button" @click="downloadWorkbook">
              {{ exporting ? '导出中...' : '下载原格式库存 Excel' }}
            </button>
            <RouterLink class="action-link ghost" to="/overview">返回仓库总览</RouterLink>
          </div>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">说明</p>
            <h3>导出规则</h3>
          </div>
          <span class="section-meta">当前模板共 22 列</span>
        </div>

        <div class="stack-list">
          <article class="note-card">
            <strong>前半段列</strong>
            <p>请购人、请购类别、项目、物料名称、规格型号、单位、供应商、库存数量、备注、区位会直接来自当前库存数据。</p>
          </article>
          <article class="note-card">
            <strong>收发列</strong>
            <p>入库日期、入库数量以及 3 组出库数量/时间/领用人，会按当前系统里最近的库存流水尽量回填。</p>
          </article>
          <article class="note-card">
            <strong>文件来源</strong>
            <p>导出会沿用当前仓库模板文件骨架，因此格式、工作表和列布局会保持一致。</p>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
