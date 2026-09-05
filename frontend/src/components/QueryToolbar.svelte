<script lang="ts">
  import { Play, Square, Save, Sparkles, Clock, Layers } from 'lucide-svelte';

  let {
    isRunning,
    statusText,
    executionTimeMs,
    rowsCount,
    onRun,
    onCancel,
    onSave
  }: {
    isRunning: boolean;
    statusText: string;
    executionTimeMs: number;
    rowsCount: number;
    onRun: () => void;
    onCancel: () => void;
    onSave: () => void;
  } = $props();
</script>

<div class="h-10 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3 select-none shrink-0">
  <!-- Левая группа кнопок управления -->
  <div class="flex items-center gap-2">
    {#if !isRunning}
      <button
        onclick={onRun}
        class="flex items-center gap-1.5 px-3 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs shadow-sm transition cursor-pointer"
        title="Выполнить текущий или выделенный запрос (Cmd+Enter / Ctrl+Enter)"
      >
        <Play class="w-3.5 h-3.5 fill-current" />
        <span>Выполнить</span>
        <span class="text-[10px] text-sky-200/80 font-mono ml-1 hidden sm:inline">⌘+↵</span>
      </button>
    {:else}
      <button
        onclick={onCancel}
        class="flex items-center gap-1.5 px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-medium text-xs shadow-sm transition cursor-pointer"
        title="Прервать выполнение на кластере"
      >
        <Square class="w-3.5 h-3.5 fill-current" />
        <span>Остановить</span>
      </button>
    {/if}

    <button
      onclick={onSave}
      class="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition cursor-pointer"
      title="Сохранить в избранное"
    >
      <Save class="w-3.5 h-3.5 text-slate-400" />
      <span class="hidden sm:inline">Сохранить</span>
    </button>
  </div>

  <!-- Правая группа статусов и метрик -->
  <div class="flex items-center gap-3 text-xs">
    {#if statusText}
      <div class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-950/70 border border-slate-800 text-slate-300">
        {#if isRunning}
          <div class="w-2 h-2 rounded-full bg-sky-400 animate-ping"></div>
        {/if}
        <span class="text-[11px] font-mono">{statusText}</span>
      </div>
    {/if}

    {#if executionTimeMs > 0}
      <div class="flex items-center gap-1 text-slate-400 font-mono text-[11px]">
        <Clock class="w-3 h-3 text-slate-500" />
        <span>{(executionTimeMs / 1000).toFixed(2)} с</span>
      </div>
    {/if}

    {#if rowsCount > 0}
      <div class="flex items-center gap-1 text-emerald-400 font-mono text-[11px] bg-emerald-950/30 border border-emerald-800/30 px-2 py-0.5 rounded">
        <Layers class="w-3 h-3 text-emerald-500" />
        <span>{rowsCount.toLocaleString()} строк</span>
      </div>
    {/if}
  </div>
</div>
