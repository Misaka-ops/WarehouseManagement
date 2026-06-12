<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

import { fetchFeishuSettings, updateFeishuSettings } from '../services/api'

const loading = ref(false)
const saving = ref(false)
const showSecret = ref(false)

const form = reactive({
  feishu_app_id: '',
  feishu_app_secret: '',
  feishu_purchase_approval_code: '',
})

function applySettings(settings: {
  feishu_app_id: string | null
  feishu_app_secret: string | null
  feishu_purchase_approval_code: string | null
}) {
  form.feishu_app_id = settings.feishu_app_id ?? ''
  form.feishu_app_secret = settings.feishu_app_secret ?? ''
  form.feishu_purchase_approval_code = settings.feishu_purchase_approval_code ?? ''
}

function getErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    return error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}

async function loadSettings() {
  loading.value = true
  try {
    applySettings(await fetchFeishuSettings())
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载飞书配置失败'))
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const response = await updateFeishuSettings({
      feishu_app_id: form.feishu_app_id || null,
      feishu_app_secret: form.feishu_app_secret || null,
      feishu_purchase_approval_code: form.feishu_purchase_approval_code || null,
    })
    applySettings(response)
    ElMessage.success('飞书配置已保存，下一次同步会直接使用新配置。')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存飞书配置失败'))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadSettings()
})
</script>

<template>
  <div class="page-stack">
    <section class="page-section hero-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">系统设置</p>
          <h3>飞书采购配置</h3>
        </div>
        <span class="section-meta">仅管理员可访问</span>
      </div>

      <p class="section-copy">
        保存后下一次飞书同步、预览、导入会直接使用这里的配置；数据库未填写的项会自动回退到后端默认配置。
      </p>
    </section>

    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">配置项</p>
          <h3>维护当前有效的飞书接入信息</h3>
        </div>
        <span class="section-meta">{{ loading ? '读取中...' : '支持留空回退默认值' }}</span>
      </div>

      <form class="settings-form-grid" @submit.prevent="saveSettings">
        <label class="field">
          <span>Feishu App ID</span>
          <input v-model="form.feishu_app_id" type="text" autocomplete="off" placeholder="请输入飞书 App ID" />
          <small class="field-hint">为空时使用后端 `.env` 中的当前默认值。</small>
        </label>

        <label class="field">
          <span>Feishu App Secret</span>
          <div class="secret-input-row">
            <input
              v-model="form.feishu_app_secret"
              :type="showSecret ? 'text' : 'password'"
              autocomplete="off"
              placeholder="请输入飞书 App Secret"
            />
            <button class="action-link ghost secret-toggle-button" type="button" @click="showSecret = !showSecret">
              {{ showSecret ? '隐藏' : '显示' }}
            </button>
          </div>
          <small class="field-hint">页面默认掩码显示，保存成功后立即用于下一次 token 获取。</small>
        </label>

        <label class="field">
          <span>采购审批编码</span>
          <input
            v-model="form.feishu_purchase_approval_code"
            type="text"
            autocomplete="off"
            placeholder="请输入飞书采购审批编码"
          />
          <small class="field-hint">采购导入页的飞书同步会使用系统设置中的这项配置。</small>
        </label>

        <div class="link-row">
          <button class="primary-button" :disabled="saving || loading" type="submit">
            {{ saving ? '保存中...' : '保存飞书配置' }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
