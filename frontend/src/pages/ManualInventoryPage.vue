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
  item_code: '',
  material_name: '',
  specification: '',
  unit: '',
  supplier_name: '',
  location_name: '',
  quantity: 1,
  total_amount: null,
  occurred_on: new Date().toISOString().slice(0, 10),
  operator_name: '',
  reference_code: 'MAN-',
  item_notes: '',
  transaction_notes: '',
})

function normalizeText(value?: string | null) {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

function resetTransactionFields() {
  form.value.quantity = 1
  form.value.total_amount = null
  form.value.occurred_on = new Date().toISOString().slice(0, 10)
  form.value.reference_code = 'MAN-'
  form.value.transaction_notes = ''
}

function fillFormFromItem(item: InventoryItem) {
  form.value.requester = item.requester ?? ''
  form.value.purchase_category = item.purchase_category ?? ''
  form.value.project_name = item.project_name ?? ''
  form.value.item_code = item.item_code ?? ''
  form.value.material_name = item.material_name
  form.value.specification = item.specification ?? ''
  form.value.unit = item.unit ?? ''
  form.value.supplier_name = item.supplier_name ?? ''
  form.value.location_name = item.location_name ?? ''
  form.value.item_notes = item.notes ?? ''
  if (!(form.value.reference_code ?? '').trim()) {
    form.value.reference_code = 'MAN-'
  }
  if (!form.value.occurred_on) {
    form.value.occurred_on = new Date().toISOString().slice(0, 10)
  }
  if (!(Number(form.value.quantity) > 0)) {
    form.value.quantity = 1
  }
  selectedCandidateId.value = item.id
}

function matchesKeyword(item: InventoryItem, keywords: string[]) {
  if (!keywords.length) {
    return true
  }

  const haystack = [
    item.material_name,
    item.item_code ?? '',
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
const normalizedUnit = computed(() => normalizeText(form.value.unit))
const normalizedSupplier = computed(() => normalizeText(form.value.supplier_name))
const normalizedLocation = computed(() => normalizeText(form.value.location_name))
const normalizedRequester = computed(() => normalizeText(form.value.requester))
const normalizedCategory = computed(() => normalizeText(form.value.purchase_category))
const normalizedProject = computed(() => normalizeText(form.value.project_name))
const normalizedItemCode = computed(() => normalizeText(form.value.item_code))
const quantityError = computed(() => (Number(form.value.quantity || 0) > 0 ? '' : '数量必须大于 0。'))
const amountError = computed(() => {
  const amount = form.value.total_amount
  if (amount == null || (typeof amount === 'number' && Number.isNaN(amount))) {
    return ''
  }

  return Number(amount) >= 0 ? '' : '金额不能小于 0。'
})

const exactMatch = computed(() => {
  if (!normalizedMaterial.value) {
    return null
  }

  return (
    inventoryItems.value.find(
      (item) =>
        item.material_name === normalizedMaterial.value &&
        normalizeText(item.specification) === normalizedSpecification.value &&
        normalizeText(item.unit) === normalizedUnit.value &&
        normalizeText(item.supplier_name) === normalizedSupplier.value &&
        normalizeText(item.location_name) === normalizedLocation.value,
    ) ?? null
  )
})

const relatedItems = computed(() => {
  const keywords = [
    normalizedMaterial.value,
    normalizedSpecification.value,
    normalizedUnit.value,
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
const projectedTotalAmount = computed(() => {
  const baseAmount = Number(exactMatch.value?.total_amount ?? 0)
  const nextAmount = Number(form.value.total_amount ?? 0)
  return Number((baseAmount + nextAmount).toFixed(2))
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

  if (quantityError.value) {
    ElMessage.warning(quantityError.value)
    return
  }

  if (amountError.value) {
    ElMessage.warning(amountError.value)
    return
  }

  submitting.value = true

  try {
    const response = await upsertInventoryItem({
      requester: normalizedRequester.value,
      purchase_category: normalizedCategory.value,
      project_name: normalizedProject.value,
      item_code: normalizedItemCode.value,
      material_name: materialName,
      specification: normalizedSpecification.value,
      unit: normalizedUnit.value,
      supplier_name: normalizedSupplier.value,
      location_name: normalizedLocation.value,
      quantity: Number(form.value.quantity),
      total_amount: form.value.total_amount == null ? null : Number(form.value.total_amount),
      occurred_on: form.value.occurred_on,
      operator_name: normalizeText(form.value.operator_name),
      reference_code: normalizeText(form.value.reference_code),
      item_notes: normalizeText(form.value.item_notes),
      transaction_notes: normalizeText(form.value.transaction_notes),
    })

    await loadDashboard({ quiet: true })
    selectedCandidateId.value = response.item.id
    resetTransactionFields()

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
          <p class="section-kicker">手动入库</p>
          <h3>先识别库存项，再填写本次入库信息</h3>
        </div>
        <span class="section-meta">适合散件、盘点修正和临时补料</span>
      </div>

      <p class="section-copy tight">
        系统会用“物料名称、规格型号、单位、供应商、区位”来判断是否补到现有库存。物品编号和库存项说明不会参与匹配；采购类别、项目和申请人只用于业务归属。
      </p>

      <div class="status-strip workflow-strip">
        <div>
          <span>步骤 1</span>
          <strong>锁定库存项</strong>
        </div>
        <div>
          <span>步骤 2</span>
          <strong>填写本次入库</strong>
        </div>
        <div>
          <span>步骤 3</span>
          <strong>确认是否新建库存</strong>
        </div>
      </div>

      <form class="form-stack manual-form" @submit.prevent="submitForm">
        <section class="subsection-panel">
          <div class="subsection-heading">
            <p>识别库存项</p>
            <span>决定是否补到已有库存</span>
          </div>

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
              <span>单位</span>
              <input v-model.trim="form.unit" type="text" placeholder="例如 件、米、包" />
            </label>

            <label class="field">
              <span>区位</span>
              <input v-model.trim="form.location_name" type="text" placeholder="例如 A-01-03" />
            </label>
          </div>

          <div class="manual-form-grid">
            <label class="field">
              <span>物品编号</span>
              <input v-model.trim="form.item_code" type="text" placeholder="例如 SKU-20260606-01" />
              <small class="field-hint">保存到库存主档，不参与合并匹配。</small>
            </label>

            <label class="field">
              <span>供应商</span>
              <input v-model.trim="form.supplier_name" type="text" placeholder="例如 深圳某某五金" />
            </label>

            <label class="field">
              <span>库存项说明</span>
              <input v-model.trim="form.item_notes" type="text" placeholder="补充长期保留的批次、来源或识别说明" />
              <small class="field-hint">保存到库存主档，不参与合并匹配。</small>
            </label>
          </div>
        </section>

        <section class="subsection-panel">
          <div class="subsection-heading">
            <p>业务归属</p>
            <span>不参与库存合并，只用于后续追踪</span>
          </div>

          <div class="manual-form-grid">
            <label class="field">
              <span>采购类别</span>
              <input v-model.trim="form.purchase_category" type="text" placeholder="例如 设备维修、办公耗材" />
            </label>

            <label class="field">
              <span>项目名称</span>
              <input v-model.trim="form.project_name" type="text" placeholder="例如 XX 项目" />
            </label>
          </div>

          <div class="manual-form-grid">
            <label class="field">
              <span>申请 / 领用人</span>
              <input v-model.trim="form.requester" type="text" placeholder="例如 张三" />
            </label>
          </div>
        </section>

        <section class="subsection-panel">
          <div class="subsection-heading">
            <p>本次入库</p>
            <span>本次动作会写入库存流水</span>
          </div>

          <div class="manual-form-grid">
            <label class="field">
              <span>数量 *</span>
              <input v-model.number="form.quantity" min="0.01" step="0.01" type="number" inputmode="decimal" />
              <small v-if="quantityError" class="field-hint danger">{{ quantityError }}</small>
            </label>

            <label class="field">
              <span>金额</span>
              <input v-model.number="form.total_amount" min="0" step="0.01" type="number" inputmode="decimal" placeholder="例如 128.50" />
              <small v-if="amountError" class="field-hint danger">{{ amountError }}</small>
              <small v-else class="field-hint">可选填写本次入库金额，台账会累计显示。</small>
            </label>

            <label class="field">
              <span>入库日期</span>
              <input v-model="form.occurred_on" type="date" />
            </label>
          </div>

          <div class="manual-form-grid">
            <label class="field">
              <span>操作人</span>
              <input v-model.trim="form.operator_name" type="text" placeholder="例如 仓管员" />
            </label>

            <label class="field">
              <span>单号 / 引用</span>
              <input v-model.trim="form.reference_code" type="text" placeholder="例如 MAN-20260530-01" />
            </label>
          </div>

          <label class="field">
            <span>本次入库说明</span>
            <textarea
              v-model.trim="form.transaction_notes"
              rows="4"
              placeholder="例如 盘点补录、拆零补料、修正来源说明"
            ></textarea>
            <small class="field-hint">只写入本次入库流水，不会覆盖库存项说明。</small>
          </label>
        </section>

        <button class="primary-button" type="submit" :disabled="submitting">
          {{ submitting ? '提交中...' : '确认手动录入' }}
        </button>
      </form>
    </section>

    <div class="page-stack">
      <section class="page-section">
        <div class="section-heading">
          <div>
            <p class="section-kicker">匹配预览</p>
            <h3>先确认会不会合并到已有库存</h3>
          </div>
          <span class="section-meta">{{ exactMatch ? `库存 #${exactMatch.id}` : '将新建' }}</span>
        </div>

        <div class="receipt-summary emphasis-summary">
          <p>{{ previewStatus }}</p>
          <p>当前库存：{{ exactMatch?.quantity_on_hand ?? 0 }} {{ exactMatch?.unit || form.unit || '件' }}</p>
          <p>提交后预计：{{ projectedQuantity }} {{ exactMatch?.unit || form.unit || '件' }}</p>
          <p>当前金额：{{ exactMatch?.total_amount ?? '--' }}</p>
          <p>提交后金额：{{ form.total_amount == null ? (exactMatch?.total_amount ?? '--') : projectedTotalAmount }}</p>
          <p>物品编号：{{ exactMatch?.item_code || normalizedItemCode || '未填写' }}</p>
          <p>区位：{{ exactMatch?.location_name || normalizedLocation || '未填写' }}</p>
          <p>本次说明：{{ form.transaction_notes?.trim() || '未填写，系统将使用默认流水说明' }}</p>
          <p>系统匹配字段：物料名称、规格型号、单位、供应商、区位</p>
          <p>物品编号仅保存到库存主档，不参与系统合并匹配</p>
        </div>

        <div class="status-strip manual-status">
          <div>
            <span>物料</span>
            <strong>{{ normalizedMaterial || '--' }}</strong>
          </div>
          <div>
            <span>单位</span>
            <strong>{{ normalizedUnit || '--' }}</strong>
          </div>
          <div>
            <span>编号</span>
            <strong>{{ normalizedItemCode || exactMatch?.item_code || '--' }}</strong>
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
            <p class="section-kicker">候选库存</p>
            <h3>可直接套用已有库存项</h3>
          </div>
          <span class="section-meta">{{ relatedItems.length }} 条</span>
        </div>

        <div class="console-table">
          <div class="console-table-scroll">
            <div class="console-table-header summary-table-grid">
              <span class="console-header-cell">物料</span>
              <span class="console-header-cell">规格</span>
              <span class="console-header-cell">单位</span>
              <span class="console-header-cell">区位</span>
              <span class="console-header-cell align-right">库存</span>
              <span class="console-header-cell">操作</span>
            </div>

            <article
              v-for="item in relatedItems"
              :key="item.id"
              class="console-table-row summary-table-grid interactive"
              role="button"
              tabindex="0"
              :class="{ active: item.id === selectedCandidateId }"
              @click="fillFormFromItem(item)"
              @keydown.enter.prevent="fillFormFromItem(item)"
              @keydown.space.prevent="fillFormFromItem(item)"
            >
              <div class="console-cell">
                <strong class="console-clamp-2" :title="item.material_name">{{ item.material_name }}</strong>
              </div>
              <div class="console-cell muted console-clamp-2" :title="item.specification || '未填规格'">{{ item.specification || '未填规格' }}</div>
              <div class="console-cell muted console-nowrap" :title="item.unit || '件'">{{ item.unit || '件' }}</div>
              <div class="console-cell muted console-clamp-2" :title="item.location_name || '未填区位'">{{ item.location_name || '未填区位' }}</div>
              <div class="console-cell align-right">
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
