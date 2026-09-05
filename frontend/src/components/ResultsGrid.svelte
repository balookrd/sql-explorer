<script lang="ts">
  import type { ColumnMeta } from '../types';
  import { Download, Search, AlertCircle, ChevronLeft, ChevronRight, FileSpreadsheet, FileJson } from 'lucide-svelte';

  let {
    columns,
    rows,
    errorMessage,
    totalRows
  }: {
    columns: ColumnMeta[];
    rows: any[][];
    errorMessage: string | null;
    totalRows: number;
  } = $props();

  let filterText = $state('');
  let currentPage = $state(1);
  let pageSize = $state(50);

  // Фильтрация строк по тексту
  const filteredRows = $derived(
    filterText.trim() === ''
      ? rows
      : rows.filter((r) =>
          r.some((cell) => String(cell).toLowerCase().includes(filterText.toLowerCase()))
        )
  );

  // Пагинация
  const totalPages = $derived(Math.max(1, Math.ceil(filteredRows.length / pageSize)));
  const paginatedRows = $derived(
    filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize)
  );

  function exportToCsv() {
    if (columns.length === 0 || rows.length === 0) return;
    const header = columns.map((c) => `"${c.name.replace(/"/g, '""')}"`).join(',');
    const body = rows
      .map((r) => r.map((val) => `"${String(val ?? '').replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([header + '\n' + body], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `query_result_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '_')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function exportToJson() {
    if (columns.length === 0 || rows.length === 0) return;
    const jsonObjects = rows.map((r) => {
      const obj: Record<string, any> = {};
      columns.forEach((col, idx) => {
        obj[col.name] = r[idx];
      });
      return obj;
    });
    const blob = new Blob([JSON.stringify(jsonObjects, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `query_result_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '_')}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="h-full w-full flex flex-col bg-slate-950 overflow-hidden select-none">
  <!-- Верхняя строка фильтрации и экспорта результатов -->
  <div class="h-9 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3 shrink-0">
    <div class="flex items-center gap-2">
      <div class="relative w-48">
        <Search class="w-3 h-3 text-slate-500 absolute left-2 top-2" />
        <input
          type="text"
          bind:value={filterText}
          placeholder="Фильтр в результатах..."
          class="w-full bg-slate-950 border border-slate-800 text-[11px] rounded pl-7 pr-2 py-0.5 text-slate-200 placeholder-slate-500 outline-none focus:border-sky-500 transition"
        />
      </div>

      <span class="text-[11px] text-slate-400">
        Показано {filteredRows.length} из {totalRows}
      </span>
    </div>

    <!-- Кнопки экспорта и пагинации -->
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-1">
        <button
          onclick={exportToCsv}
          disabled={rows.length === 0}
          class="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-[11px] border border-slate-700 transition cursor-pointer"
          title="Скачать в формате CSV"
        >
          <FileSpreadsheet class="w-3 h-3 text-emerald-400" />
          <span>CSV</span>
        </button>

        <button
          onclick={exportToJson}
          disabled={rows.length === 0}
          class="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-[11px] border border-slate-700 transition cursor-pointer"
          title="Скачать в формате JSON"
        >
          <FileJson class="w-3 h-3 text-amber-400" />
          <span>JSON</span>
        </button>
      </div>

      <!-- Пагинация -->
      <div class="flex items-center gap-1 text-[11px] text-slate-400">
        <button
          onclick={() => (currentPage = Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          class="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 cursor-pointer"
        >
          <ChevronLeft class="w-3 h-3" />
        </button>
        <span class="px-1">{currentPage} / {totalPages}</span>
        <button
          onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
          class="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 cursor-pointer"
        >
          <ChevronRight class="w-3 h-3" />
        </button>
      </div>
    </div>
  </div>

  <!-- Область таблицы или ошибки -->
  <div class="flex-1 overflow-auto">
    {#if errorMessage}
      <div class="p-4 m-3 rounded-lg bg-red-950/40 border border-red-800/60 text-red-300 flex items-start gap-3 text-xs">
        <AlertCircle class="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div>
          <div class="font-semibold mb-1">Ошибка исполнения запроса</div>
          <div class="font-mono text-[11px] whitespace-pre-wrap">{errorMessage}</div>
        </div>
      </div>
    {:else if columns.length === 0}
      <div class="h-full flex items-center justify-center text-slate-600 text-xs">
        Результаты выполнения запроса появятся здесь
      </div>
    {:else}
      <table class="w-full text-left border-collapse font-mono text-[11px]">
        <thead class="sticky top-0 bg-slate-900 border-b border-slate-800 z-10 shadow-sm">
          <tr>
            <th class="py-1.5 px-3 border-r border-slate-800 text-slate-500 w-12 text-right">#</th>
            {#each columns as col}
              <th class="py-1.5 px-3 border-r border-slate-800 text-slate-300 font-semibold whitespace-nowrap">
                <div>{col.name}</div>
                <div class="text-[9px] text-slate-500 font-normal">{col.type}</div>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/60">
          {#each paginatedRows as row, rIdx}
            <tr class="hover:bg-slate-800/40 transition">
              <td class="py-1 px-3 border-r border-slate-800/60 text-slate-600 text-right">
                {(currentPage - 1) * pageSize + rIdx + 1}
              </td>
              {#each row as cell}
                <td class="py-1 px-3 border-r border-slate-800/60 text-slate-300 whitespace-nowrap max-w-xs truncate">
                  {#if cell === null || cell === undefined}
                    <span class="text-slate-600 italic">null</span>
                  {:else}
                    {String(cell)}
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>
