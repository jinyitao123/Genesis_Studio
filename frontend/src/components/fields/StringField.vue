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
  get: () => String(props.modelValue ?? ''),
  set: (val: string) => emit('update:model-value', val),
});

const placeholder = computed(() => props.field.placeholder || `输入${props.field.label}`);
</script>

<template>
  <div class="string-field" :class="{ 'has-error': error }">
    <input
      v-model="inputValue"
      type="text"
      class="field-input"
      :placeholder="placeholder"
      :required="field.required"
    />
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.string-field {
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
}

.field-input:focus {
  outline: none;
  border-color: #0d6c8d;
  box-shadow: 0 0 0 2px rgba(13, 108, 141, 0.1);
}

.string-field.has-error .field-input {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
