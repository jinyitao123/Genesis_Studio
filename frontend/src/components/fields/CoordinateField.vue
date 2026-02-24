<script setup lang="ts">
import { computed } from 'vue';
import type { InspectorFieldSchema } from '@/types';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: { x: number; y: number; z?: number }): void;
}>();

interface CoordinateValue {
  x: number;
  y: number;
  z?: number;
}

const coordinate = computed({
  get: (): CoordinateValue => {
    const val = props.modelValue;
    if (val && typeof val === 'object' && 'x' in val && 'y' in val) {
      return val as CoordinateValue;
    }
    return { x: 0, y: 0, z: 0 };
  },
  set: (val: CoordinateValue) => emit('update:model-value', val),
});

function updateCoord(axis: 'x' | 'y' | 'z', value: string) {
  const num = parseFloat(value);
  if (!isNaN(num)) {
    emit('update:model-value', { ...coordinate.value, [axis]: num });
  }
}
</script>

<template>
  <div class="coordinate-field" :class="{ 'has-error': error }">
    <div class="coordinate-inputs">
      <div class="coord-input">
        <label>X</label>
        <input
          :value="coordinate.x"
          type="number"
          step="0.1"
          @input="e => updateCoord('x', (e.target as HTMLInputElement).value)"
        />
      </div>
      <div class="coord-input">
        <label>Y</label>
        <input
          :value="coordinate.y"
          type="number"
          step="0.1"
          @input="e => updateCoord('y', (e.target as HTMLInputElement).value)"
        />
      </div>
      <div class="coord-input">
        <label>Z</label>
        <input
          :value="coordinate.z"
          type="number"
          step="0.1"
          @input="e => updateCoord('z', (e.target as HTMLInputElement).value)"
        />
      </div>
    </div>
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.coordinate-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coordinate-inputs {
  display: flex;
  gap: 8px;
}

.coord-input {
  display: flex;
  align-items: center;
  gap: 4px;
}

.coord-input label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  width: 16px;
}

.coord-input input {
  width: 70px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 12px;
  font-family: 'Monaco', 'Consolas', monospace;
}

.coord-input input:focus {
  outline: none;
  border-color: #0d6c8d;
}

.coordinate-field.has-error .coord-input input {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
