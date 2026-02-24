import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { AuthUser, TokenPair, UserRole } from '@/types';

export function useAuthStore() {
  return defineStore('auth', () => {
    // State
    const token = ref<string>('');
    const refreshToken = ref<string>('');
    const user = ref<AuthUser | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Getters
    const isAuthenticated = computed(() => !!token.value);
    const userRole = computed(() => user.value?.role as UserRole | undefined);
    const canWrite = computed(() => 
      userRole.value === 'Admin' || userRole.value === 'Designer' || userRole.value === 'Operator'
    );
    const isAdmin = computed(() => userRole.value === 'Admin');

    // Actions
    async function login(username: string, password: string): Promise<boolean> {
      loading.value = true;
      error.value = null;
      try {
        const response = await apiPost<{ access_token: string; role: string }>('/api/auth/token', {
          username,
          password,
        });
        token.value = response.access_token;
        // Decode token to get user info (simplified)
        try {
          const payload = JSON.parse(atob(response.access_token.split('.')[1]));
          user.value = {
            username: payload.sub || username,
            role: response.role as UserRole,
            permissions: payload.permissions || [],
          };
        } catch {
          user.value = { username, role: response.role as UserRole };
        }
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Login failed';
        return false;
      } finally {
        loading.value = false;
      }
    }

    async function loginWithRefresh(): Promise<boolean> {
      if (!refreshToken.value) return false;
      loading.value = true;
      error.value = null;
      try {
        const response = await apiPost<TokenPair>('/api/auth/token/pair', {
          username: user.value?.username || '',
          password: '', // Not needed for refresh
        });
        token.value = response.access_token;
        refreshToken.value = response.refresh_token;
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Token refresh failed';
        logout();
        return false;
      } finally {
        loading.value = false;
      }
    }

    async function refreshAccessToken(): Promise<boolean> {
      if (!refreshToken.value) return false;
      loading.value = true;
      error.value = null;
      try {
        const response = await apiPost<TokenPair>('/api/auth/refresh', {
          refresh_token: refreshToken.value,
        });
        token.value = response.access_token;
        refreshToken.value = response.refresh_token;
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Token refresh failed';
        logout();
        return false;
      } finally {
        loading.value = false;
      }
    }

    function logout(): void {
      token.value = '';
      refreshToken.value = '';
      user.value = null;
      error.value = null;
    }

    function ensureToken(): Promise<void> {
      return new Promise((resolve) => {
        if (token.value) {
          resolve();
        } else {
          // Auto-login with default credentials for MVP
          login('designer', 'designer').then(() => resolve());
        }
      });
    }

    // Initialize with default token
    function init(): Promise<void> {
      return ensureToken();
    }

    return {
      // State
      token,
      refreshToken,
      user,
      loading,
      error,
      // Getters
      isAuthenticated,
      userRole,
      canWrite,
      isAdmin,
      // Actions
      login,
      loginWithRefresh,
      refreshAccessToken,
      logout,
      ensureToken,
      init,
    };
  })();
}
