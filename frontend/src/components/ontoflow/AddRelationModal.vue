<script setup lang="ts">
import { ref, computed } from 'vue';
import type { OFClass } from '@/types';

const props = defineProps<{
  classes: OFClass[];
  existingNames: string[];
}>();

const emit = defineEmits<{
  confirm: [name: string, sourceId: string, targetId: string, description: string];
  cancel: [];
}>();

const name = ref('');
const sourceId = ref('');
const targetId = ref('');
const description = ref('');

const isReflexive = computed(() => sourceId.value && sourceId.value === targetId.value);
const nameHint = computed(() =>
  isReflexive.value ? '关系类型建议：自反关系（如hasFriend）' : ''
);
const nameError = computed(() => {
  if (!name.value) return '';
  if (props.existingNames.includes(name.value.trim())) return '关系名已存在';
  return '';
});
const canSubmit = computed(
  () => name.value.trim().length > 0 && sourceId.value && targetId.value && !nameError.value
);

function submit() {
  if (!canSubmit.value) return;
  emit('confirm', name.value.trim(), sourceId.value, targetId.value, description.value.trim());
}
</script>

<template>
  <div class="of-modal-overlay" @click.self="emit('cancel')">
    <div class="of-modal" style="width:520px">
      <h3 class="of-modal__title">🔗 添加关系</h3>
      <div class="of-field">
        <label class="of-label">源类</label>
        <select v-model="sourceId" class="of-input">
          <option value="">— 选择源类 —</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="of-field">
        <label class="of-label">目标类</label>
        <select v-model="targetId" class="of-input">
          <option value="">— 选择目标类 —</option>
          <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="of-field">
        <label class="of-label">关系名 <span class="of-required">*</span></label>
        <input
          v-model="name"
          class="of-input"
          :class="{ 'of-input--error': nameError }"
          placeholder="关系名（例如：hasFriend）"
          @keyup.enter="submit"
        />
        <p v-if="nameHint && !nameError" class="of-hint">{{ nameHint }}</p>
        <p v-if="nameError" class="of-error">{{ nameError }}</p>
      </div>
      <div class="of-field">
        <label class="of-label">描述</label>
        <textarea
          v-model="description"
          class="of-input of-textarea"
          style="height:60px"
          placeholder="关系描述（例如：表示两人之间的友谊）"
        />
      </div>
      <div class="of-modal__actions">
        <button class="of-btn of-btn--ghost" @click="emit('cancel')">Cancel</button>
        <button class="of-btn of-btn--primary" :disabled="!canSubmit" @click="submit">Create Relation</button>
      </div>
    </div>
  </div>
</template>
