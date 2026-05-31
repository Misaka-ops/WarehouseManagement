<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuth } from '../composables/useAuth'


const route = useRoute()
const router = useRouter()
const { isAuthenticating, login } = useAuth()

const username = ref('')
const password = ref('')

const submitDisabled = computed(() => !username.value.trim() || !password.value.trim() || isAuthenticating.value)

async function handleLogin() {
  if (submitDisabled.value) {
    return
  }

  try {
    await login({
      username: username.value.trim(),
      password: password.value,
    })
    ElMessage.success('登录成功。')

    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/'
    await router.replace(redirect)
  } catch (error) {
    const message = axios.isAxiosError(error)
      ? (error.response?.data?.detail as string | undefined) || error.message || '登录失败'
      : error instanceof Error
        ? error.message
        : '登录失败'
    ElMessage.error(message)
  }
}
</script>

<template>
  <div class="page-stack">
    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">权限控制</p>
          <h3>登录后开启完整仓储操作</h3>
        </div>
        <span class="section-meta">管理员</span>
      </div>

      <div class="receipt-summary emphasis-summary">
        <p>游客模式：仅开放库存台账基础查询。</p>
        <p>登录后：可查看金额、供应商，并执行导入、收货、入库、出库和同步操作。</p>
        <p>默认管理员账号：admin / admin</p>
      </div>
    </section>

    <section class="page-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">管理员登录</p>
          <h3>输入账号密码</h3>
        </div>
        <span class="section-meta">Auth</span>
      </div>

      <form class="form-stack login-form" autocomplete="off" @submit.prevent="handleLogin">
        <label class="field">
          <span>账号</span>
          <input
            v-model="username"
            name="warehouse-login-username"
            type="text"
            autocomplete="off"
            autocapitalize="off"
            autocorrect="off"
            spellcheck="false"
            placeholder="请输入账号"
          />
        </label>

        <label class="field">
          <span>密码</span>
          <input
            v-model="password"
            name="warehouse-login-password"
            type="password"
            autocomplete="new-password"
            autocapitalize="off"
            autocorrect="off"
            spellcheck="false"
            placeholder="请输入密码"
          />
        </label>

        <div class="link-row">
          <RouterLink class="action-link ghost" to="/overview">先以游客身份查看台账</RouterLink>
        </div>

        <button class="primary-button" :disabled="submitDisabled" type="submit">
          {{ isAuthenticating ? '登录中...' : '登录并进入系统' }}
        </button>
      </form>
    </section>
  </div>
</template>
