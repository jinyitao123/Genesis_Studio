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

const options = computed(() => props.field.options || []);

const selectedValue = computed({
  get: () => String(props.modelValue ?? ''),
  set: (val: string) => emit('update:model-value', val),
});
</script>

<template>
  <div class="enum-field" :class="{ 'has-error': error }">
    <select v-model="selectedValue" class="field-select" :required="field.required">
      <option value="" disabled>选择{{ field.label }}</option>
      <option v-for="option in options" :key="option" :value="option">
        {{ option }}
      </option>
    </select>
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.enum-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
  background: #fff;
  cursor: pointer;
}

.field-select:focus {
  outline: none;
  border-color: #0d6c8d;
  box-shadow: 0 0 0 2px rgba(13, 108, 141, 0.1);
}

.enum-field.has-error .field-select {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
