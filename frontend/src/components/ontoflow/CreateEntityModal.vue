<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { OFClass } from '@/types';

const props = defineProps<{
  classes: OFClass[];
}>();

const emit = defineEmits<{
  confirm: [classId: string, properties: Record<string, string | number | null>];
  cancel: [];
}>();

const selectedClassId = ref('');
const propValues = ref<Record<string, string>>({});
const propErrors = ref<Record<string, string>>({});

const selectedClass = computed(() =>
  props.classes.find(c => c.id === selectedClassId.value) ?? null
);

watch(selectedClassId, () => {
  propValues.value = {};
  propErrors.value = {};
  if (selectedClass.value) {
    for (const p of selectedClass.value.properties) {
      propValues.value[p.name] = '';
    }
  }
});

function validate(): boolean {
  propErrors.value = {};
  let ok = true;
  if (!selectedClass.value) return false;
  for (const prop of selectedClass.value.properties) {
    const val = propValues.value[prop.name] ?? '';
    if (prop.type === 'number' && val !== '') {
      if (isNaN(Number(val))) {
        propErrors.value[prop.name] = '必须为数字';
        ok = false;
      }
    }
  }
  return ok;
}

const canSubmit = computed(() => !!selectedClassId.value);

function submit() {
  if (!canSubmit.value || !validate()) return;
  const cls = selectedClass.value!;
  const props: Record<string, string | number | null> = {};
  for (const prop of cls.properties) {
    const raw = propValues.value[prop.name] ?? '';
    if (prop.type === 'number' && raw !== '') {
      props[prop.name] = Number(raw);
    } else {
      props[prop.name] = raw || null;
    }
  }
  emit('confirm', selectedClassId.value, props);
}
</script>

<template>
  <div class="of-modal-overlay" @click.self="emit('cancel')">
    <div class="of-modal" style="width:450px; max-height:80vh; overflow-y:auto">
      <h3 class="of-modal__title">创建实体</h3>
      <div class="of-field">
        <label class="of-label">选择类</label>
        <select v-model="selectedClassId" class="of-input">
          <option value="">— 选择类 —</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <template v-if="selectedClass">
        <div v-for="prop in selectedClass.properties" :key="prop.id" class="of-field">
          <label class="of-label">{{ prop.name }}</label>
          <input
            v-model="propValues[prop.name]"
            class="of-input"
            :class="{ 'of-input--error': propErrors[prop.name] }"
            :type="prop.type === 'number' ? 'number' : 'text'"
            :placeholder="prop.type === 'number' ? '数字' : '文本'"
          />
          <p v-if="propErrors[prop.name]" class="of-error">{{ propErrors[prop.name] }}</p>
        </div>
        <p v-if="selectedClass.properties.length === 0" class="of-hint">该类暂无属性</p>
      </template>
      <div class="of-modal__actions">
        <button class="of-btn of-btn--ghost" @click="emit('cancel')">Cancel</button>
        <button class="of-btn of-btn--primary" :disabled="!canSubmit" @click="submit">Create Entity</button>
      </div>
    </div>
  </div>
</template>
