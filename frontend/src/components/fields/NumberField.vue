<script setup lang="ts">
import { computed } from 'vue';
import type { InspectorFieldSchema } from '@/types';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: number): void;
}>();

const inputValue = computed({
  get: () => {
    const val = props.modelValue;
    if (typeof val === 'number' && !isNaN(val)) return val;
    return props.field.defaultValue !== undefined ? Number(props.field.defaultValue) : 0;
  },
  set: (val: string) => {
    const num = parseFloat(val);
    if (!isNaN(num)) {
      emit('update:model-value', num);
    }
  },
});

const min = computed(() => props.field.min);
const max = computed(() => props.field.max);
const step = computed(() => props.field.fieldType === 'integer' ? 1 : 0.1);
</script>

<template>
  <div class="number-field" :class="{ 'has-error': error }">
    <input
      v-model="inputValue"
      type="number"
      class="field-input"
      :min="min"
      :max="max"
      :step="step"
      :required="field.required"
    />
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.number-field {
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

.number-field.has-error .field-input {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
