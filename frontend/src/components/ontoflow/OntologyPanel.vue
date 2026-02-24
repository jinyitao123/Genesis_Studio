<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import type { OFClass, OFRelation } from '@/types';
import AddPropertyModal from './AddPropertyModal.vue';

const props = defineProps<{
  classes: OFClass[];
  relations: OFRelation[];
}>();

const emit = defineEmits<{
  addClass: [];
  deleteClass: [classId: string];
  addProperty: [classId: string, name: string, type: 'string' | 'number', unique: boolean];
  deleteProperty: [classId: string, propId: string];
  addRelation: [];
  deleteRelation: [relationId: string];
}>();

const propModalClassId = ref<string | null>(null);
const openMenuId = ref<string | null>(null);

function toggleMenu(id: string) {
  openMenuId.value = openMenuId.value === id ? null : id;
}
function closeMenu() {
  openMenuId.value = null;
}

onMounted(() => { document.addEventListener('click', closeMenu); });
onBeforeUnmount(() => { document.removeEventListener('click', closeMenu); });

function openAddProperty(classId: string) {
  propModalClassId.value = classId;
  closeMenu();
}

function onPropertyConfirm(name: string, type: 'string' | 'number', unique: boolean) {
  if (propModalClassId.value) {
    emit('addProperty', propModalClassId.value, name, type, unique);
  }
  propModalClassId.value = null;
}

function classForRelation(classId: string) {
  return props.classes.find(c => c.id === classId)?.name ?? classId;
}
</script>

<template>
  <aside class="of-panel">
    <!-- Add Class button -->
    <div class="of-panel__section-header">
      <span class="of-panel__section-title">类 (Classes)</span>
      <button class="of-btn of-btn--icon" title="Add Class" @click="emit('addClass')">＋</button>
    </div>

    <!-- Class cards -->
    <div class="of-class-list">
      <div
        v-for="cls in classes"
        :key="cls.id"
        class="of-class-card"
      >
        <div class="of-class-card__header">
          <span class="of-class-card__name">{{ cls.name }}</span>
          <span class="of-class-card__count">({{ cls.properties.length }} properties)</span>
          <div class="of-menu-wrapper">
            <button class="of-btn of-btn--icon of-btn--sm" @click.stop="toggleMenu(cls.id)">⋮</button>
            <ul v-if="openMenuId === cls.id" class="of-menu">
              <li @click="openAddProperty(cls.id)">Add Property</li>
              <li class="of-menu__danger" @click="emit('deleteClass', cls.id); closeMenu()">Delete Class</li>
            </ul>
          </div>
        </div>
        <p v-if="cls.description" class="of-class-card__desc">{{ cls.description }}</p>

        <!-- Properties -->
        <ul class="of-prop-list">
          <li
            v-for="prop in cls.properties"
            :key="prop.id"
            class="of-prop-item"
          >
            <span class="of-prop-item__name">{{ prop.name }}</span>
            <span class="of-prop-item__meta">({{ prop.type }}{{ prop.unique ? ', 唯一' : '' }})</span>
            <button
              class="of-btn of-btn--icon of-btn--xs of-btn--danger"
              title="删除属性"
              @click="emit('deleteProperty', cls.id, prop.id)"
            >✕</button>
          </li>
        </ul>
      </div>

      <p v-if="classes.length === 0" class="of-empty">暂无类，点击 ＋ 创建</p>
    </div>

    <!-- Relations -->
    <div class="of-panel__section-header" style="margin-top:16px">
      <span class="of-panel__section-title">关系 (Relations)</span>
      <button class="of-btn of-btn--icon" title="Add Relation" @click="emit('addRelation')">🔗</button>
    </div>
    <ul class="of-rel-list">
      <li v-for="rel in relations" :key="rel.id" class="of-rel-item">
        <span>{{ classForRelation(rel.source_class_id) }} → {{ classForRelation(rel.target_class_id) }}: <b>{{ rel.name }}</b></span>
        <button
          class="of-btn of-btn--icon of-btn--xs of-btn--danger"
          title="删除关系"
          @click="emit('deleteRelation', rel.id)"
        >✕</button>
      </li>
      <li v-if="relations.length === 0" class="of-empty">暂无关系</li>
    </ul>

    <!-- Add Property Modal -->
    <AddPropertyModal
      v-if="propModalClassId !== null"
      :existing-names="classes.find(c => c.id === propModalClassId)?.properties.map(p => p.name) ?? []"
      @confirm="onPropertyConfirm"
      @cancel="propModalClassId = null"
    />
  </aside>
</template>
