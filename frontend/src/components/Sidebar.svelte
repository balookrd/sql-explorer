<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../api/client';
  import type { QueryHistoryItem, ColumnMeta } from '../types';
  import QueueView from './QueueView.svelte';
  import {
    Database,
    Folder,
    Table,
    History,
    Search,
    RefreshCw,
    ChevronRight,
    ChevronDown,
    Clock,
    CheckCircle2,
    XCircle,
    Play,
    ListOrdered
  } from 'lucide-svelte';

  let {
    clusterId,
    onSelectTable,
    onSelectHistoryQuery,
    onLoadCachedResult
  }: {
    clusterId: string;
    onSelectTable: (tableName: string) => void;
    onSelectHistoryQuery: (queryText: string) => void;
    onLoadCachedResult: (queryId: string, clusterName: string) => void;
  } = $props();

  let activeTab = $state<'schema' | 'queue' | 'history'>('schema');
  let searchQuery = $state('');
  let loadingSchema = $state(false);
  let loadingHistory = $state(false);
  let queueViewRef: QueueView | null = null;

  // Схема
  let catalogs = $state<string[]>([]);
  let selectedCatalog = $state<string>('tpch');
  let schemas = $state<string[]>([]);
  let expandedSchemas = $state<Record<string, boolean>>({});
  let tablesBySchema = $state<Record<string, string[]>>({});
  let expandedTables = $state<Record<string, boolean>>({});
  let columnsByTable = $state<Record<string, ColumnMeta[]>>({});

  // История
  let historyItems = $state<QueryHistoryItem[]>([]);

  $effect(() => {
    if (clusterId) {
      loadCatalogTree();
    }
  });

  async function loadCatalogTree() {
    loadingSchema = true;
    try {
      const cats = await api.getCatalogs(clusterId);
      catalogs = cats.length ? cats : ['default'];
      selectedCatalog = catalogs[0];
      await loadSchemas(selectedCatalog);
    } catch (err) {
      console.error('Ошибка загрузки каталогов', err);
    } finally {
      loadingSchema = false;
    }
  }

  async function loadSchemas(cat: string) {
    try {
      schemas = await api.getSchemas(clusterId, cat);
      expandedSchemas = {};
      if (schemas.length > 0) {
        toggleSchema(schemas[0]);
      }
    } catch (err) {
      console.error('Ошибка загрузки схем', err);
    }
  }

  async function toggleSchema(sch: string) {
    expandedSchemas[sch] = !expandedSchemas[sch];
    if (expandedSchemas[sch] && !tablesBySchema[sch]) {
      try {
        const tbls = await api.getTables(clusterId, selectedCatalog, sch);
        tablesBySchema[sch] = tbls;
      } catch (err) {
        console.error('Ошибка загрузки таблиц', err);
      }
    }
  }

  async function toggleTable(sch: string, tbl: string) {
    const key = `${sch}.${tbl}`;
    expandedTables[key] = !expandedTables[key];
    if (expandedTables[key] && !columnsByTable[key]) {
      try {
        const cols = await api.getColumns(clusterId, selectedCatalog, sch, tbl);
        columnsByTable[key] = cols;
      } catch (err) {
        console.error('Ошибка загрузки колонок', err);
      }
    }
  }

  export async function refreshHistory() {
    loadingHistory = true;
    try {
      historyItems = await api.getHistory();
    } catch (err) {
      console.error('Ошибка загрузки истории', err);
    } finally {
      loadingHistory = false;
    }
    if (queueViewRef) {
      queueViewRef.refreshQueue();
    }
  }

  export function refreshQueue() {
    if (queueViewRef) {
      queueViewRef.refreshQueue();
    }
  }

  function handleTabChange(tab: 'schema' | 'queue' | 'history') {
    activeTab = tab;
    if (tab === 'history') {
      refreshHistory();
    } else if (tab === 'queue' && queueViewRef) {
      queueViewRef.refreshQueue();
    }
  }

  onMount(() => {
    refreshHistory();
  });
</script>

<aside class="w-80 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 select-none overflow-hidden h-full">
  <!-- Вкладки сайдбара -->
  <div class="flex border-b border-slate-800 bg-slate-950/50 p-1 gap-1 shrink-0">
    <button
      onclick={() => handleTabChange('schema')}
      class="flex-1 flex items-center justify-center gap-1 py-1.5 text-xs font-medium rounded transition cursor-pointer {activeTab === 'schema' ? 'bg-slate-800 text-sky-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200'}"
    >
      <Database class="w-3.5 h-3.5" />
      <span>Схема</span>
    </button>

    <button
      onclick={() => handleTabChange('queue')}
      class="flex-1 flex items-center justify-center gap-1 py-1.5 text-xs font-medium rounded transition cursor-pointer {activeTab === 'queue' ? 'bg-slate-800 text-sky-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200'}"
    >
      <ListOrdered class="w-3.5 h-3.5" />
      <span>Очередь</span>
    </button>

    <button
      onclick={() => handleTabChange('history')}
      class="flex-1 flex items-center justify-center gap-1 py-1.5 text-xs font-medium rounded transition cursor-pointer {activeTab === 'history' ? 'bg-slate-800 text-sky-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200'}"
    >
      <History class="w-3.5 h-3.5" />
      <span>История</span>
    </button>
  </div>

  {#if activeTab === 'schema'}
    <!-- Поиск и фильтр схемы -->
    <div class="p-2 border-b border-slate-800 flex flex-col gap-2 shrink-0">
      {#if catalogs.length > 1}
        <div class="flex items-center gap-1.5 text-xs text-slate-400">
          <span>Каталог:</span>
          <select
            bind:value={selectedCatalog}
            onchange={() => loadSchemas(selectedCatalog)}
            class="flex-1 bg-slate-800 text-slate-200 text-xs rounded px-2 py-1 outline-none border border-slate-700"
          >
            {#each catalogs as cat}
              <option value={cat}>{cat}</option>
            {/each}
          </select>
        </div>
      {/if}

      <div class="relative">
        <Search class="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Поиск таблиц..."
          class="w-full bg-slate-950/80 border border-slate-800 text-xs rounded-md pl-8 pr-2.5 py-1.5 text-slate-200 placeholder-slate-500 outline-none focus:border-sky-500 transition"
        />
      </div>
    </div>

    <!-- Дерево объектов схемы -->
    <div class="flex-1 overflow-y-auto p-2 text-xs">
      {#if loadingSchema}
        <div class="flex items-center justify-center py-8 text-slate-500 gap-2">
          <RefreshCw class="w-4 h-4 animate-spin" />
          <span>Загрузка схемы...</span>
        </div>
      {:else}
        {#each schemas as sch}
          <div class="mb-1">
            <button
              onclick={() => toggleSchema(sch)}
              class="w-full flex items-center gap-1.5 px-1.5 py-1 rounded hover:bg-slate-800 text-slate-300 font-medium text-left transition cursor-pointer"
            >
              {#if expandedSchemas[sch]}
                <ChevronDown class="w-3.5 h-3.5 text-slate-500 shrink-0" />
              {:else}
                <ChevronRight class="w-3.5 h-3.5 text-slate-500 shrink-0" />
              {/if}
              <Folder class="w-3.5 h-3.5 text-amber-500/80 shrink-0" />
              <span class="truncate">{sch}</span>
            </button>

            {#if expandedSchemas[sch]}
              <div class="pl-4 mt-0.5 space-y-0.5 border-l border-slate-800/80 ml-2">
                {#if tablesBySchema[sch]}
                  {#each (tablesBySchema[sch] || []).filter(t => !searchQuery || t.toLowerCase().includes(searchQuery.toLowerCase())) as tbl}
                    <div>
                      <div class="flex items-center justify-between group rounded hover:bg-slate-800/80 px-1.5 py-1">
                        <button
                          onclick={() => toggleTable(sch, tbl)}
                          class="flex items-center gap-1.5 text-slate-400 group-hover:text-slate-200 text-left truncate flex-1 cursor-pointer"
                        >
                          {#if expandedTables[`${sch}.${tbl}`]}
                            <ChevronDown class="w-3 h-3 text-slate-500 shrink-0" />
                          {:else}
                            <ChevronRight class="w-3 h-3 text-slate-500 shrink-0" />
                          {/if}
                          <Table class="w-3.5 h-3.5 text-sky-400/80 shrink-0" />
                          <span class="truncate">{tbl}</span>
                        </button>

                        <button
                          onclick={() => onSelectTable(`${selectedCatalog}.${sch}.${tbl}`)}
                          title="Вставить SELECT в редактор"
                          class="opacity-0 group-hover:opacity-100 p-1 hover:bg-sky-500/20 text-sky-400 rounded transition cursor-pointer"
                        >
                          <Play class="w-2.5 h-2.5" />
                        </button>
                      </div>

                      {#if expandedTables[`${sch}.${tbl}`] && columnsByTable[`${sch}.${tbl}`]}
                        <div class="pl-4 py-1 space-y-1 border-l border-slate-800/80 ml-2">
                          {#each columnsByTable[`${sch}.${tbl}`] as col}
                            <div class="flex items-center justify-between text-[11px] text-slate-400 pr-2">
                              <span class="truncate text-slate-300 font-mono">{col.name}</span>
                              <span class="text-[10px] text-slate-500 font-mono shrink-0 ml-1">{col.type}</span>
                            </div>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/each}
                {:else}
                  <div class="text-[11px] text-slate-500 py-1 pl-2">Загрузка таблиц...</div>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

  {:else if activeTab === 'queue'}
    <!-- Вкладка Очередь задач -->
    <div class="flex-1 overflow-hidden">
      <QueueView
        bind:this={queueViewRef}
        onLoadResult={onLoadCachedResult}
        onInsertQuery={onSelectHistoryQuery}
      />
    </div>

  {:else}
    <!-- Вкладка История запросов -->
    <div class="flex-1 overflow-y-auto p-2 space-y-2 text-xs">
      <div class="flex items-center justify-between pb-1 mb-1 border-b border-slate-800 text-[11px] text-slate-400 px-1">
        <span>История выполненных запросов</span>
        <button
          onclick={refreshHistory}
          class="hover:text-sky-400 transition cursor-pointer p-0.5"
          title="Обновить"
        >
          <RefreshCw class="w-3 h-3 {loadingHistory ? 'animate-spin' : ''}" />
        </button>
      </div>

      {#if historyItems.length === 0}
        <div class="text-center py-8 text-slate-500">История запросов пуста</div>
      {:else}
        {#each historyItems as item}
          <div
            class="p-2 rounded-lg bg-slate-950/60 hover:bg-slate-800 border border-slate-800/80 transition flex flex-col gap-1 group"
          >
            <div class="flex items-center justify-between text-[10px]">
              <span class="font-semibold text-slate-300 truncate">{item.cluster_name}</span>
              {#if item.status === 'FINISHED'}
                <span class="flex items-center gap-1 text-emerald-400 font-medium">
                  <CheckCircle2 class="w-2.5 h-2.5" />
                  {item.rows_count} стр.
                </span>
              {:else if item.status === 'CANCELLED'}
                <span class="text-slate-400 font-medium">Остановлен</span>
              {:else if item.status === 'FAILED'}
                <span class="flex items-center gap-1 text-red-400 font-medium">
                  <XCircle class="w-2.5 h-2.5" />
                  Ошибка
                </span>
              {:else}
                <span class="text-sky-400 font-medium">{item.status}</span>
              {/if}
            </div>

            <div
              onclick={() => onSelectHistoryQuery(item.query_text)}
              title="Вставить SQL в редактор"
              class="font-mono text-[11px] text-slate-400 group-hover:text-slate-200 line-clamp-2 break-all cursor-pointer"
            >
              {item.query_text}
            </div>

            <div class="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-900">
              <span class="flex items-center gap-1">
                <Clock class="w-2.5 h-2.5" />
                {Math.round(item.execution_time_ms)} мс
              </span>

              {#if item.has_cached_result}
                <button
                  onclick={() => onLoadCachedResult(item.id, item.cluster_name)}
                  class="text-sky-400 hover:text-sky-300 font-medium cursor-pointer"
                >
                  Смотреть данные →
                </button>
              {:else}
                <span>{new Date(item.created_at).toLocaleTimeString()}</span>
              {/if}
            </div>
          </div>
        {/each}
      {/if}
    </div>
  {/if}
</aside>
