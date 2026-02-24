<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import * as monaco from 'monaco-editor';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';

// Setup Monaco workers
self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') return new jsonWorker();
    if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker();
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker();
    if (label === 'typescript' || label === 'javascript') return new tsWorker();
    return new editorWorker();
  }
};

interface Props {
  modelValue?: string;
  language?: string;
  theme?: string;
  readOnly?: boolean;
  minimap?: boolean;
  lineNumbers?: 'on' | 'off' | 'relative';
  height?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  language: 'json',
  theme: 'vs-dark',
  readOnly: false,
  minimap: false,
  lineNumbers: 'on',
  height: '100%',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'change', value: string): void;
  (e: 'save'): void;
}>();

const editorContainer = ref<HTMLDivElement | null>(null);
const editor = ref<monaco.editor.IStandaloneCodeEditor | null>(null);
const isFocused = ref(false);

// Editor options
const editorOptions = computed(() => ({
  readOnly: props.readOnly,
  minimap: { enabled: props.minimap },
  lineNumbers: props.lineNumbers,
  theme: props.theme,
  automaticLayout: true,
  scrollBeyondLastLine: false,
  fontSize: 14,
  fontFamily: "'Fira Code', 'Consolas', monospace",
  tabSize: 2,
  wordWrap: 'on',
  folding: true,
  lineDecorationsWidth: 10,
  renderLineHighlight: 'all',
  contextmenu: true,
  quickSuggestions: true,
  suggestOnTriggerCharacters: true,
  acceptSuggestionOnEnter: 'on',
  tabCompletion: 'on',
  wordBasedSuggestions: 'currentDocument',
}));

// Initialize editor
onMounted(() => {
  if (!editorContainer.value) return;
  
  editor.value = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: props.language,
    ...editorOptions.value,
  });
  
  // Listen for content changes
  editor.value.onDidChangeModelContent(() => {
    const value = editor.value?.getValue() || '';
    emit('update:modelValue', value);
    emit('change', value);
  });
  
  // Focus state
  editor.value.onDidFocusEditorText(() => {
    isFocused.value = true;
  });
  
  editor.value.onDidBlurEditorText(() => {
    isFocused.value = false;
  });
  
  // Save handler (Ctrl+S)
  editor.value.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    emit('save');
  });
  
  // Format document (Shift+Alt+F)
  editor.value.addCommand(
    monaco.KeyMod.Shift | monaco.KeyMod.Alt | monaco.KeyCode.KeyF,
    () => {
      editor.value?.getAction('editor.action.formatDocument')?.run();
    }
  );
  
  // Add default custom theme
  monaco.editor.defineTheme('genesis-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
      { token: 'keyword', foreground: '569CD6' },
      { token: 'string', foreground: 'CE9178' },
      { token: 'number', foreground: 'B5CEA8' },
      { token: 'type', foreground: '4EC9B0' },
    ],
    colors: {
      'editor.background': '#1A1A2E',
      'editor.foreground': '#D4D4D4',
      'editor.lineHighlightBackground': '#252540',
      'editorLineNumber.foreground': '#6A6A8A',
      'editorLineNumber.activeForeground': '#FFFFFF',
      'editor.selectionBackground': '#264F78',
      'editor.inactiveSelectionBackground': '#264F7855',
    },
  });
  
  monaco.editor.setTheme('genesis-dark');
});

// Watch for prop changes
watch(() => props.modelValue, (newValue) => {
  if (editor.value && newValue !== editor.value.getValue()) {
    editor.value.setValue(newValue);
  }
});

watch(() => props.language, (newLang) => {
  if (editor.value) {
    const model = editor.value.getModel();
    if (model) {
      monaco.editor.setModelLanguage(model, newLang);
    }
  }
});

watch(() => props.readOnly, (readonly) => {
  editor.value?.updateOptions({ readOnly: readonly });
});

// Cleanup
onUnmounted(() => {
  editor.value?.dispose();
});

// Expose methods
function format() {
  editor.value?.getAction('editor.action.formatDocument')?.run();
}

function focus() {
  editor.value?.focus();
}

function setValue(value: string) {
  editor.value?.setValue(value);
}

function getValue(): string {
  return editor.value?.getValue() || '';
}

function insertText(text: string) {
  const position = editor.value?.getPosition();
  if (position && editor.value) {
    editor.value.trigger('keyboard', 'type', { text });
  }
}

defineExpose({
  format,
  focus,
  setValue,
  getValue,
  insertText,
});
</script>

<template>
  <div class="code-editor" :class="{ focused: isFocused }">
    <div class="editor-toolbar" v-if="!readOnly">
      <div class="toolbar-left">
        <span class="language-badge">{{ language.toUpperCase() }}</span>
      </div>
      <div class="toolbar-right">
        <button class="toolbar-btn" @click="format" title="格式化 (Shift+Alt+F)">
          <span>📐</span>
        </button>
        <button class="toolbar-btn" @click="emit('save')" title="保存 (Ctrl+S)">
          <span>💾</span>
        </button>
      </div>
    </div>
    <div ref="editorContainer" class="editor-container" :style="{ height }"></div>
    <div class="editor-status" v-if="!readOnly">
      <span class="status-item">
        <kbd>Ctrl+S</kbd> 保存
      </span>
      <span class="status-item">
        <kbd>Shift+Alt+F</kbd> 格式化
      </span>
      <span class="status-item language-info">
        {{ language }}
      </span>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: 'CodeEditor'
};
</script>

<style scoped>
.code-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid #3d3d5c;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
  transition: border-color 0.2s ease;
}

.code-editor.focused {
  border-color: #4a9eff;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252540;
  border-bottom: 1px solid #3d3d5c;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.language-badge {
  padding: 4px 8px;
  background: #3d3d5c;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  text-transform: uppercase;
}

.toolbar-btn {
  padding: 6px 10px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.toolbar-btn:hover {
  background: #3d3d5c;
}

.toolbar-btn:active {
  transform: scale(0.95);
}

.editor-container {
  flex: 1;
  min-height: 300px;
}

.editor-status {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 6px 12px;
  background: #252540;
  border-top: 1px solid #3d3d5c;
  font-size: 11px;
  color: #8a8aa3;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-item kbd {
  padding: 2px 6px;
  background: #3d3d5c;
  border-radius: 3px;
  font-family: inherit;
  font-size: 10px;
}

.language-info {
  margin-left: auto;
  opacity: 0.7;
}
</style>
