import { computed, reactive, readonly } from 'vue'

import { fetchAuthSession, postLogin, registerUnauthorizedHandler, setApiAccessToken } from '../services/api'
import type { AuthLoginPayload, AuthLoginResponse, AuthUser } from '../types/inventory'


const STORAGE_KEY = 'warehouse-admin-access-token'

type AuthState = {
  initialized: boolean
  restoring: boolean
  authenticating: boolean
  accessToken: string
  user: AuthUser | null
  expiresAt: string | null
}

const state = reactive<AuthState>({
  initialized: false,
  restoring: false,
  authenticating: false,
  accessToken: readStoredToken(),
  user: null,
  expiresAt: null,
})

setApiAccessToken(state.accessToken)
registerUnauthorizedHandler(() => {
  clearAuthState()
})

function readStoredToken() {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.localStorage.getItem(STORAGE_KEY)?.trim() ?? ''
}

function persistToken(token: string) {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(STORAGE_KEY, token)
}

function clearStoredToken() {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.removeItem(STORAGE_KEY)
}

function applySession(response: AuthLoginResponse | { access_token: string; user: AuthUser; expires_at: string }) {
  state.accessToken = response.access_token
  state.user = response.user
  state.expiresAt = response.expires_at
  persistToken(response.access_token)
  setApiAccessToken(response.access_token)
}

function clearAuthState() {
  state.accessToken = ''
  state.user = null
  state.expiresAt = null
  clearStoredToken()
  setApiAccessToken(null)
}

async function restoreSession() {
  state.restoring = true

  try {
    if (!state.accessToken) {
      clearAuthState()
      return
    }

    const session = await fetchAuthSession()
    if (session.authenticated && session.user && session.expires_at) {
      applySession({
        access_token: state.accessToken,
        user: session.user,
        expires_at: session.expires_at,
      })
      return
    }

    clearAuthState()
  } catch {
    clearAuthState()
  } finally {
    state.restoring = false
    state.initialized = true
  }
}

async function login(payload: AuthLoginPayload) {
  state.authenticating = true
  try {
    const response = await postLogin(payload)
    applySession(response)
    state.initialized = true
    return response
  } finally {
    state.authenticating = false
  }
}

function logout() {
  clearAuthState()
  state.initialized = true
}

export function useAuth() {
  return {
    state: readonly(state),
    currentUser: computed(() => state.user),
    expiresAt: computed(() => state.expiresAt),
    isAuthenticated: computed(() => Boolean(state.user && state.accessToken)),
    isReady: computed(() => state.initialized && !state.restoring),
    isRestoring: computed(() => state.restoring),
    isAuthenticating: computed(() => state.authenticating),
    login,
    logout,
    restoreSession,
  }
}
