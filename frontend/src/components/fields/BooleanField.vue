<script setup lang="ts">
import { computed } from 'vue';
import type { InspectorFieldSchema } from '@/types';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: boolean): void;
}>();

const isChecked = computed({
  get: () => Boolean(props.modelValue),
  set: (val: boolean) => emit('update:model-value', val),
});
</script>

<template>
  <div class="boolean-field" :class="{ 'has-error': error }">
    <label class="toggle-label">
      <input
        v-model="isChecked"
        type="checkbox"
        class="toggle-input"
      />
      <span class="toggle-switch"></span>
      <span class="toggle-text">{{ isChecked ? '是' : '否' }}</span>
    </label>
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.boolean-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle-input {
  display: none;
}

.toggle-switch {
  display: inline-block;
  width: 40px;
  height: 22px;
  background: #d1d5db;
  border-radius: 11px;
  position: relative;
  transition: background 0.2s;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.toggle-input:checked + .toggle-switch {
  background: #10b981;
}

.toggle-input:checked + .toggle-switch::after {
  transform: translateX(18px);
}

.toggle-text {
  font-size: 13px;
  color: #374151;
}

.boolean-field.has-error .toggle-switch {
  background: #fecaca;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
