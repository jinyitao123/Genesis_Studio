<script setup lang="ts">
import { computed } from 'vue';
import type { InspectorFieldSchema } from '@/types';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: unknown): void;
}>();

// Derived fields are read-only - they are computed from other fields
const displayValue = computed(() => {
  const val = props.modelValue;
  if (val === null || val === undefined) return '-';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
});

function isEditable() {
  // Derived fields are typically read-only, but can be made editable
  return false;
}
</script>

<template>
  <div class="derived-field" :class="{ 'has-error': error }">
    <div class="derived-display">
      <span class="derived-value">{{ displayValue }}</span>
      <span class="derived-badge">计算</span>
    </div>
    <span v-if="error" class="field-error">{{ error }}</span>
    <p v-if="field.helpText" class="field-help">{{ field.helpText }}</p>
  </div>
</template>

<style scoped>
.derived-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.derived-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.derived-value {
  flex: 1;
  font-size: 13px;
  font-family: 'Monaco', 'Consolas', monospace;
  color: #6b7280;
}

.derived-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 4px;
  text-transform: uppercase;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}

.field-help {
  margin: 4px 0 0;
  font-size: 11px;
  color: #9ca3af;
}
</style>
