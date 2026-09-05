<script lang="ts">
  import type { UserSession, ClusterSummary } from '../types';
  import { Database, Shield, User, LogOut, ChevronDown, Cpu, Server } from 'lucide-svelte';

  let {
    user,
    clusters,
    selectedClusterId = $bindable(),
    onLogout
  }: {
    user: UserSession | null;
    clusters: ClusterSummary[];
    selectedClusterId: string;
    onLogout: () => void;
  } = $props();

  let showUserMenu = $state(false);

  const activeCluster = $derived(
    clusters.find((c) => c.id === selectedClusterId) || clusters[0]
  );
</script>

<header class="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 select-none shrink-0 z-20">
  <!-- Логотип и Бренд -->
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-lg bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400 font-bold">
      <Database class="w-4 h-4" />
    </div>
    <div class="flex flex-col">
      <span class="text-sm font-semibold tracking-wide text-slate-100 flex items-center gap-1.5">
        SQL Explorer
        <span class="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">
          Trino & Hive
        </span>
      </span>
    </div>
  </div>

  <!-- Селектор кластеров и имперсонация -->
  <div class="flex items-center gap-3">
    <div class="flex items-center gap-2 bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-1.5">
      <Server class="w-4 h-4 text-slate-400" />
      <span class="text-xs text-slate-400 font-medium">Кластер:</span>
      <select
        bind:value={selectedClusterId}
        class="bg-transparent text-xs font-semibold text-slate-200 outline-none cursor-pointer pr-2"
      >
        {#each clusters as c}
          <option value={c.id} class="bg-slate-900 text-slate-200">
            {c.name} ({c.type.toUpperCase()})
          </option>
        {/each}
      </select>

      {#if activeCluster}
        <div class="h-3 w-px bg-slate-700 mx-1"></div>
        <div class="flex items-center gap-1.5 text-[11px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
          <Cpu class="w-3 h-3" />
          <span>doAs: <strong class="font-mono">{user?.username}</strong></span>
        </div>
      {/if}
    </div>
  </div>

  <!-- Профиль пользователя и LDAP / Kerberos инфо -->
  <div class="relative">
    <button
      onclick={() => (showUserMenu = !showUserMenu)}
      class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 transition cursor-pointer text-left"
    >
      <div class="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-slate-300">
        <User class="w-3.5 h-3.5" />
      </div>
      <div class="flex flex-col">
        <span class="text-xs font-medium text-slate-200 leading-tight">
          {user?.display_name || user?.username || 'Гость'}
        </span>
        <span class="text-[10px] text-slate-400 leading-tight">
          {user?.auth_method?.toUpperCase()} SSO
        </span>
      </div>
      <ChevronDown class="w-3.5 h-3.5 text-slate-400 ml-1" />
    </button>

    {#if showUserMenu && user}
      <div class="absolute right-0 mt-2 w-64 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-3 z-50">
        <div class="border-b border-slate-800 pb-2.5 mb-2.5">
          <div class="text-xs font-semibold text-slate-200">{user.display_name}</div>
          <div class="text-[11px] text-slate-400 font-mono">@{user.username}</div>
          {#if user.email}
            <div class="text-[11px] text-slate-400 mt-0.5">{user.email}</div>
          {/if}
        </div>

        <!-- Группы LDAP / ACL -->
        <div class="mb-3">
          <div class="text-[11px] font-medium text-slate-400 mb-1.5 flex items-center justify-between">
            <span>Группы LDAP / Роли:</span>
            {#if user.is_admin}
              <span class="flex items-center gap-0.5 text-amber-400 text-[10px] font-bold">
                <Shield class="w-3 h-3" /> ADMIN
              </span>
            {/if}
          </div>
          <div class="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
            {#each user.groups as group}
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {group}
              </span>
            {/each}
          </div>
        </div>

        <button
          onclick={() => {
            showUserMenu = false;
            onLogout();
          }}
          class="w-full flex items-center justify-center gap-2 py-1.5 px-3 rounded bg-red-950/40 hover:bg-red-900/60 border border-red-800/50 text-red-300 text-xs font-medium transition cursor-pointer"
        >
          <LogOut class="w-3.5 h-3.5" />
          Выйти из системы
        </button>
      </div>
    {/if}
  </div>
</header>
