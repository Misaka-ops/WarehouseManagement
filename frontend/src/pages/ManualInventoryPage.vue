<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { useInventoryWorkspace } from '../composables/useInventoryWorkspace'
import { upsertInventoryItem } from '../services/api'
import type { InventoryItem, InventoryManualUpsertPayload } from '../types/inventory'

const { inventoryItems, loadDashboard } = useInventoryWorkspace()

const submitting = ref(false)
const selectedCandidateId = ref<number | null>(null)

const form = ref<InventoryManualUpsertPayload>({
  requester: '',
  purchase_category: '',
  project_name: '',
  material_name: '',
  specification: '',
  unit: '',
  supplier_name: '',
  location_name: '',
  quantity: 1,
  occurred_on: new Date().toISOString().slice(0, 10),
  operator_name: '',
  reference_code: '',
  notes: '',
})

function normalizeText(value?: string | null) {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

function resetTransactionFields() {
  form.value.quantity = 1
  form.value.occurred_on = new Date().toISOString().slice(0, 10)
  form.value.operator_name = ''
  form.value.reference_code = ''
}

function fillFormFromItem(item: InventoryItem) {
  form.value.requester = item.requester ?? ''
  form.value.purchase_category = item.purchase_category ?? ''
  form.value.project_name = item.project_name ?? ''
  form.value.material_name = item.material_name
  form.value.specification = item.specification ?? ''
  form.value.unit = item.unit ?? ''
  form.value.supplier_name = item.supplier_name ?? ''
  form.value.location_name = item.location_name ?? ''
  form.value.notes = item.notes ?? ''
  resetTransactionFields()
  selectedCandidateId.value = item.id
}

function matchesKeyword(item: InventoryItem, keywords: string[]) {
  if (!keywords.length) {
    return true
  }

  const haystack = [
    item.material_name,
    item.specification ?? '',
    item.unit ?? '',
    item.supplier_name ?? '',
    item.location_name ?? '',
    item.requester ?? '',
    item.purchase_category ?? '',
    item.project_name ?? '',
    item.notes ?? '',
  ]
    .join(' ')
    .toLowerCase()

  return keywords.every((keyword) => haystack.includes(keyword))
}

const normalizedMaterial = computed(() => form.value.material_name.trim())
const normalizedSpecification = computed(() => normalizeText(form.value.specification))
const normalizedSupplier = computed(() => normalizeText(form.value.supplier_name))
const normalizedLocation = computed(() => normalizeText(form.value.location_name))

const exactMatch = computed(() => {
  if (!normalizedMaterial.value) {
    return null
  }

  return (
    inventoryItems.value.find(
      (item) =>
        item.material_name === normalizedMaterial.value &&
        normalizeText(item.specification) === normalizedSpecification.value &&
        normalizeText(item.supplier_name) === normalizedSupplier.value &&
        normalizeText(item.location_name) === normalizedLocation.value,
    ) ?? null
  )
})

const relatedItems = computed(() => {
  const keywords = [
    normalizedMaterial.value,
    normalizedSpecification.value,
    normalizedSupplier.value,
    normalizedLocation.value,
  ]
    .filter((value): value is string => Boolean(value))
    .map((value) => value.toLowerCase())

  if (!keywords.length) {
    return inventoryItems.value.slice(0, 8)
  }

  return inventoryItems.value.filter((item) => matchesKeyword(item, keywords)).slice(0, 8)
})

const projectedQuantity = computed(() => {
  const baseQuantity = Number(exactMatch.value?.quantity_on_hand ?? 0)
  const nextQuantity = Number(form.value.quantity || 0)
  return Number((baseQuantity + nextQuantity).toFixed(2))
})

const previewStatus = computed(() => {
  if (exactMatch.value) {
    return `将补到现有库存 #${exactMatch.value.id}`
  }
  if (!normalizedMaterial.value) {
    return '先输入物料名称，系统会检查是否已有相同库存。'
  }
  return '未找到完全匹配项，提交后会自动新建库存记录。'
})

async function submitForm() {
  const materialName = normalizedMaterial.value
  if (!materialName) {
    ElMessage.warning('请先填写物料名称。')
    return
  }

  if (Number(form.value.quantity || 0) <= 0) {
    ElMessage.warning('数量必须大于 0。')
    return
  }

  submitting.value = true

  try {
    const response = await upsertInventoryItem({
      requester: normalizeText(form.value.requester),
      purchase_category: normalizeText(form.value.purchase_category),
      project_name: normalizeText(form.value.project_name),
      material_name: materialName,
      specification: normalizedSpecification.value,
      unit: normalizeText(form.value.unit),
      supplier_name: normalizedSupplier.value,
      location_name: normalizedLocation.value,
      quantity: Number(form.value.quantity),
      occurred_on: form.value.occurred_on,
      operator_name: normalizeText(form.value.operator_name),
      reference_code: normalizeText(form.value.reference_code),
      notes: normalizeText(form.value.notes),
    })

    await loadDashboard({ quiet: true })
    form.value.quantity = 1
    form.value.occurred_on = new Date().toISOString().slice(0, 10)
    form.value.operator_name = ''
    form.value.reference_code = ''
    selectedCandidateId.value = response.item.id

    ElMessage.success(response.created_item ? '已新建库存项并完成手动入库。' : '已补充到现有库存。')
  } catch (error) {
    const message = axios.isAxiosError(error)
      ? (error.response?.data?.detail as string | undefined) || error.message || '提交失败'
      : error instanceof Error
        ? error.message
        : '提交失败'
    ElMessage.error(message)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadDashboard()
})
</script>

<template>
  <div class="content-grid">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">维护</p>
          <h3>手动录入 / 补库存</h3>
        </div>
        <span class="section-meta">可新建，也可按相同物料自动累加</span>
      </div>

      <p class="section-copy tight">适合散件、临时补料、现场盘点后补录等场景。提交后会自动写入库存流水。</p>

      <form class="form-stack manual-form" @submit.prevent="submitForm">
        <div class="manual-form-grid">
          <label class="field">
            <span>物料名称 *</span>
            <input v-model.trim="form.material_name" type="text" placeholder="例如 螺丝 M4 x 12" />
          </label>

          <label class="field">
            <span>规格型号</span>
            <input v-model.trim="form.specification" type="text" placeholder="例如 304 不锈钢" />
          </label>
        </div>

        <div class="manual-form-grid">
          <label class="field">
            <span>数量 *</span>
            <input v-model.number="form.quantity" min="0.01" step="0.01" type="number" />
          </label>

          <label class="field">
            <span>单位</span>
            <input v-model.trim="form.unit" type="text" placeholder="例如 件、米、包" />
          </label>
        </div>

        <div class="manual-form-grid">
          <label class="field">
            <span>供应商</span>
            <input v-model.trim="form.supplier_name" type="text" placeholder="例如 深圳某某五金" />
          </label>

          <label class="field">
            <span>区位</span>
            <input v-model.trim="form.location_name" type="text" placeholder="例如 A-01-03" />
          </label>
        </div>

        <div class="manual-form-grid">
          <label class="field">
            <span>领用/采购人</span>
            <input v-model.trim="form.requester" type="text" placeholder="例如 张三" />
          </label>

          <label class="field">
            <span>采购类别 / 项目</span>
            <input v-model.trim="form.project_name" type="text" placeholder="例如 设备维修 / XX项目" />
          </label>
        </div>

        <div class="manual-form-grid">
          <label class="field">
            <span>入库日期</span>
            <input v-model="form.occurred_on" type="date" />
          </label>

          <label class="field">
            <span>操作人</span>
            <input v-model.trim="form.operator_name" type="text" placeholder="例如 仓管员" />
          </label>
        </div>

        <label class="field">
          <span>单号 / 引用</span>
          <input v-model.trim="form.reference_code" type="text" placeholder="例如 MAN-20260530-01" />
        </label>

        <label class="field">
          <span>备注</span>
          <textarea v-model.trim="form.notes" rows="4" placeholder="补充本次手动录入原因、来源、批次等"></textarea>
        </label>

        <button class="primary-button" type="submit" :disabled="submitting">
          {{ submitting ? '提交中...' : '确认手动录入' }}
        </button>
      </form>
    </section>

    <div class="page-stack">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">预览</p>
            <h3>匹配结果</h3>
          </div>
          <span class="section-meta">{{ exactMatch ? `库存 #${exactMatch.id}` : '新建' }}</span>
        </div>

        <div class="receipt-summary">
          <p>{{ previewStatus }}</p>
          <p>当前库存：{{ exactMatch?.quantity_on_hand ?? 0 }} {{ exactMatch?.unit || form.unit || '件' }}</p>
          <p>提交后预计：{{ projectedQuantity }} {{ exactMatch?.unit || form.unit || '件' }}</p>
          <p>区位：{{ exactMatch?.location_name || normalizedLocation || '未填写' }}</p>
        </div>

        <div class="status-strip manual-status">
          <div>
            <span>物料</span>
            <strong>{{ normalizedMaterial || '--' }}</strong>
          </div>
          <div>
            <span>供应商</span>
            <strong>{{ normalizedSupplier || '--' }}</strong>
          </div>
          <div>
            <span>区位</span>
            <strong>{{ normalizedLocation || '--' }}</strong>
          </div>
        </div>
      </section>

      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">候选</p>
            <h3>可套用库存项</h3>
          </div>
          <span class="section-meta">{{ relatedItems.length }} 条</span>
        </div>

        <div class="console-table">
          <div class="console-table-scroll">
            <div class="console-table-header summary-table-grid">
              <span class="console-header-cell">物料</span>
              <span class="console-header-cell">规格</span>
              <span class="console-header-cell">区位</span>
              <span class="console-header-cell">供应商</span>
              <span class="console-header-cell">库存</span>
              <span class="console-header-cell">操作</span>
            </div>

            <article
              v-for="item in relatedItems"
              :key="item.id"
              class="console-table-row summary-table-grid interactive"
              :class="{ active: item.id === selectedCandidateId }"
              @click="fillFormFromItem(item)"
            >
              <div class="console-cell">
                <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
                <span class="console-subtext">#{{ item.id }}</span>
              </div>
              <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
              <div class="console-cell muted console-clamp-2" :title="item.location_name || '未填区位'">{{ item.location_name || '未填区位' }}</div>
              <div class="console-cell muted console-clamp-2" :title="item.supplier_name || '未填供应商'">{{ item.supplier_name || '未填供应商' }}</div>
              <div class="console-cell">
                <span class="console-badge info">{{ item.quantity_on_hand }} {{ item.unit || '件' }}</span>
              </div>
              <div class="console-row-actions" @click.stop>
                <button class="console-action primary" type="button" @click="fillFormFromItem(item)">套用</button>
              </div>
            </article>
          </div>

          <div v-if="!relatedItems.length" class="console-empty">还没有可参考的库存项。</div>
        </div>
      </section>
    </div>
  </div>
</template>
