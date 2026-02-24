<script setup lang="ts">
import { ref, computed } from 'vue';
import type { OFClass } from '@/types';

const props = defineProps<{
  classes: OFClass[];
}>();

const emit = defineEmits<{
  confirm: [file: File, classId: string];
  cancel: [];
}>();

const selectedClassId = ref('');
const selectedFile = ref<File | null>(null);
const csvColumns = ref<string[]>([]);
const fileInputRef = ref<HTMLInputElement | null>(null);

const selectedClass = computed(() =>
  props.classes.find(c => c.id === selectedClassId.value) ?? null
);

const propNames = computed(() =>
  selectedClass.value ? new Set(selectedClass.value.properties.map(p => p.name)) : new Set<string>()
);

interface ColumnMatch {
  csv_column: string;
  matched: boolean;
}

const columnMatches = computed<ColumnMatch[]>(() =>
  csvColumns.value.map(col => ({
    csv_column: col,
    matched: propNames.value.has(col),
  }))
);

const hasAnyMatch = computed(() => columnMatches.value.some(m => m.matched));
const canImport = computed(() => !!selectedFile.value && !!selectedClassId.value && hasAnyMatch.value);

function onFileChange(evt: Event) {
  const input = evt.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  selectedFile.value = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    const text = (e.target?.result as string) ?? '';
    const firstLine = text.split('\n')[0] ?? '';
    csvColumns.value = firstLine.split(',').map(c => c.trim().replace(/^"|"$/g, ''));
  };
  reader.readAsText(file);
}

function submit() {
  if (!canImport.value || !selectedFile.value) return;
  emit('confirm', selectedFile.value, selectedClassId.value);
}
</script>

<template>
  <div class="of-modal-overlay" @click.self="emit('cancel')">
    <div class="of-modal" style="width:600px">
      <h3 class="of-modal__title">📤 Import CSV</h3>

      <div class="of-field">
        <label class="of-label">目标类</label>
        <select v-model="selectedClassId" class="of-input">
          <option value="">— 选择类 —</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>

      <div class="of-field">
        <label class="of-label">CSV 文件</label>
        <input ref="fileInputRef" type="file" accept=".csv,text/csv" style="display:none" @change="onFileChange" />
        <button class="of-btn of-btn--ghost" @click="fileInputRef?.click()">
          {{ selectedFile ? selectedFile.name : '选择文件...' }}
        </button>
      </div>

      <!-- Column match table -->
      <div v-if="csvColumns.length > 0 && selectedClass" class="of-match-table">
        <div class="of-match-table__header">
          <span>本体属性</span>
          <span>CSV 列名</span>
          <span>匹配</span>
        </div>
        <div
          v-for="match in columnMatches"
          :key="match.csv_column"
          class="of-match-table__row"
        >
          <span>{{ match.matched ? match.csv_column : '—' }}</span>
          <span>{{ match.csv_column }}</span>
          <span :class="match.matched ? 'of-match--ok' : 'of-match--warn'">
            {{ match.matched ? '✅' : '⚠️' }}
          </span>
        </div>
        <p v-if="!hasAnyMatch" class="of-error" style="margin-top:8px">无法导入：无匹配本体属性</p>
      </div>

      <div class="of-modal__actions">
        <button class="of-btn of-btn--ghost" @click="emit('cancel')">Cancel</button>
        <button class="of-btn of-btn--primary" :disabled="!canImport" @click="submit">Import</button>
      </div>
    </div>
  </div>
</template>
