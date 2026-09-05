<script lang="ts">
  import { api } from '../api/client';
  import type { UserSession } from '../types';
  import { Database, Lock, User, KeyRound, ShieldAlert, CheckCircle2, ArrowRight } from 'lucide-svelte';

  let {
    onLoginSuccess
  }: {
    onLoginSuccess: (user: UserSession) => void;
  } = $props();

  let username = $state('analyst_user');
  let password = $state('password123');
  let errorMessage = $state<string | null>(null);
  let loading = $state(false);

  async function handleLdapLogin(e?: Event) {
    if (e) e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    loading = true;
    errorMessage = null;

    try {
      const res = await api.login(username, password);
      onLoginSuccess(res.user);
    } catch (err: any) {
      errorMessage = err.message || 'Ошибка входа в систему';
    } finally {
      loading = false;
    }
  }

  async function handleKerberosLogin() {
    loading = true;
    errorMessage = null;

    try {
      const res = await api.kerberosNegotiate();
      onLoginSuccess(res.user);
    } catch (err: any) {
      errorMessage = err.message || 'Kerberos SPNEGO SSO не вернул билет';
    } finally {
      loading = false;
    }
  }

  function pickMockUser(u: string, p: string) {
    username = u;
    password = p;
  }
</script>

<div class="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 z-50 select-none">
  <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 flex flex-col gap-5">
    <!-- Шапка -->
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
        <Database class="w-5 h-5" />
      </div>
      <div>
        <h2 class="text-base font-semibold text-slate-100">Вход в SQL Explorer</h2>
        <p class="text-xs text-slate-400">Trino & Hive Enterprise Web Portal</p>
      </div>
    </div>

    {#if errorMessage}
      <div class="p-3 rounded-lg bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-start gap-2">
        <ShieldAlert class="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
        <span>{errorMessage}</span>
      </div>
    {/if}

    <!-- Кнопка Kerberos SSO -->
    <button
      type="button"
      onclick={handleKerberosLogin}
      disabled={loading}
      class="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50"
    >
      <KeyRound class="w-4 h-4 text-sky-400" />
      <span>Войти через Kerberos SPNEGO (SSO)</span>
    </button>

    <div class="flex items-center gap-2 text-[11px] text-slate-500">
      <div class="h-px bg-slate-800 flex-1"></div>
      <span>или учетная запись LDAPS</span>
      <div class="h-px bg-slate-800 flex-1"></div>
    </div>

    <!-- Форма LDAPS -->
    <form onsubmit={handleLdapLogin} class="flex flex-col gap-3">
      <div>
        <label class="block text-[11px] font-medium text-slate-400 mb-1">Имя пользователя (LDAP sAMAccountName)</label>
        <div class="relative">
          <User class="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            bind:value={username}
            placeholder="например, ivanov"
            class="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-sky-500 transition"
            required
          />
        </div>
      </div>

      <div>
        <label class="block text-[11px] font-medium text-slate-400 mb-1">Пароль домена</label>
        <div class="relative">
          <Lock class="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="password"
            bind:value={password}
            placeholder="••••••••"
            class="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-sky-500 transition"
            required
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        class="w-full mt-2 py-2 px-3 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md flex items-center justify-center gap-1.5 transition cursor-pointer disabled:opacity-50"
      >
        <span>{loading ? 'Проверка прав...' : 'Войти в систему'}</span>
        <ArrowRight class="w-3.5 h-3.5" />
      </button>
    </form>

    <!-- Быстрый выбор тестовых пользователей (для демонстрации) -->
    <div class="pt-3 border-t border-slate-800/80">
      <div class="text-[10px] text-slate-500 mb-2 font-medium">Быстрый вход для демо/тестирования ACL:</div>
      <div class="flex flex-col gap-1.5 text-[11px]">
        <button
          type="button"
          onclick={() => pickMockUser('analyst_user', 'password123')}
          class="flex items-center justify-between p-1.5 rounded bg-slate-950/60 hover:bg-slate-800 border border-slate-800/60 text-slate-300 text-left transition cursor-pointer"
        >
          <div>
            <div class="font-medium">Анна Аналитикова (analyst_user)</div>
            <div class="text-[10px] text-slate-500">Группы: bi-analysts (Trino + Apache Hive)</div>
          </div>
          <CheckCircle2 class="w-3.5 h-3.5 text-sky-400 opacity-60" />
        </button>

        <button
          type="button"
          onclick={() => pickMockUser('de_user', 'password123')}
          class="flex items-center justify-between p-1.5 rounded bg-slate-950/60 hover:bg-slate-800 border border-slate-800/60 text-slate-300 text-left transition cursor-pointer"
        >
          <div>
            <div class="font-medium">Иван Датаинженеров (de_user)</div>
            <div class="text-[10px] text-slate-500">Группы: data-engineers (полный доступ к Hortonworks Hive)</div>
          </div>
          <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400 opacity-60" />
        </button>
      </div>
    </div>
  </div>
</div>
