<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as monaco from 'monaco-editor';

  let {
    value = $bindable(),
    onExecute
  }: {
    value: string;
    onExecute: (queryToRun: string) => void;
  } = $props();

  let editorContainer: HTMLDivElement;
  let editorInstance: monaco.editor.IStandaloneCodeEditor | null = null;

  onMount(() => {
    // Регистрация кастомных ключевых слов Trino и Hive в синтаксисе SQL
    monaco.languages.registerCompletionItemProvider('sql', {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn
        };

        const trinoHiveKeywords = [
          'APPROX_DISTINCT', 'ARBITRARY', 'ARRAY_AGG', 'CARDINALITY', 'CAST',
          'COALESCE', 'CONCAT', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP',
          'DATE_ADD', 'DATE_DIFF', 'DATE_FORMAT', 'DATE_PARSE', 'DATE_TRUNC',
          'FLATTEN', 'FROM_ISO8601_TIMESTAMP', 'FROM_UNIXTIME', 'JSON_ARRAY_CONTAINS',
          'JSON_EXTRACT', 'JSON_EXTRACT_SCALAR', 'JSON_PARSE', 'JSON_SIZE',
          'LEAD', 'LAG', 'NOW', 'PARTITION', 'REGEXP_EXTRACT', 'REGEXP_LIKE',
          'ROW_NUMBER', 'SPLIT', 'TRY', 'TRY_CAST', 'UNNEST', 'ZIP'
        ];

        const suggestions: monaco.languages.CompletionItem[] = trinoHiveKeywords.map((kw) => ({
          label: kw,
          kind: monaco.languages.CompletionItemKind.Function,
          insertText: kw,
          range: range,
          detail: 'Trino/Hive Function'
        }));

        return { suggestions };
      }
    });

    editorInstance = monaco.editor.create(editorContainer, {
      value: value,
      language: 'sql',
      theme: 'vs-dark',
      automaticLayout: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Monaco, 'Courier New', monospace",
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      lineNumbers: 'on',
      renderLineHighlight: 'all',
      padding: { top: 12, bottom: 12 },
      quickSuggestions: true,
      tabSize: 2
    });

    // Слушатель изменений содержимого
    editorInstance.onDidChangeModelContent(() => {
      if (editorInstance) {
        value = editorInstance.getValue();
      }
    });

    // Шорткат Cmd+Enter / Ctrl+Enter для выполнения
    editorInstance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      triggerExecution();
    });
  });

  export function triggerExecution() {
    if (!editorInstance) return;
    const selection = editorInstance.getSelection();
    const selectedText = selection && !selection.isEmpty()
      ? editorInstance.getModel()?.getValueInRange(selection)
      : null;

    const queryToRun = selectedText?.trim() || editorInstance.getValue().trim();
    if (queryToRun) {
      onExecute(queryToRun);
    }
  }

  // Обновление значения снаружи (например при клике на историю или сниппет)
  $effect(() => {
    if (editorInstance && value !== editorInstance.getValue()) {
      editorInstance.setValue(value);
    }
  });

  onDestroy(() => {
    if (editorInstance) {
      editorInstance.dispose();
    }
  });
</script>

<div class="h-full w-full relative overflow-hidden flex flex-col bg-[#1e1e1e]">
  <div bind:this={editorContainer} class="flex-1 w-full h-full"></div>
</div>
