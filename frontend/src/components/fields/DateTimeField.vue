<script setup lang="ts">
import { computed } from 'vue';
import type { InspectorFieldSchema } from '@/types';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: string): void;
}>();

const inputValue = computed({
  get: () => {
    const val = props.modelValue;
    if (typeof val === 'string') {
      // Format as ISO datetime for input
      return val;
    }
    if (val instanceof Date) {
      return val.toISOString().slice(0, 16);
    }
    return '';
  },
  set: (val: string) => emit('update:model-value', val),
});

const min = computed(() => props.field.validation?.config?.min);
const max = computed(() => props.field.validation?.config?.max);
</script>

<template>
  <div class="datetime-field" :class="{ 'has-error': error }">
    <input
      v-model="inputValue"
      type="datetime-local"
      class="field-input"
      :min="min"
      :max="max"
      :required="field.required"
    />
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.datetime-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-input {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
  font-family: 'Monaco', 'Consolas', monospace;
}

.field-input:focus {
  outline: none;
  border-color: #0d6c8d;
  box-shadow: 0 0 0 2px rgba(13, 108, 141, 0.1);
}

.datetime-field.has-error .field-input {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
