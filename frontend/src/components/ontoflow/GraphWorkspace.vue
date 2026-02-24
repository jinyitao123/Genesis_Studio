<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import cytoscape from 'cytoscape';
import type { Core, NodeSingular } from 'cytoscape';
import type { OFClass, OFRelation, OFEntity, OFLink } from '@/types';

const props = defineProps<{
  classes: OFClass[];
  relations: OFRelation[];
  entities: OFEntity[];
  links: OFLink[];
}>();

const emit = defineEmits<{
  createLink: [sourceEntityId: string, targetEntityId: string, relationId: string];
  patchLinkLabel: [linkId: string, label: string];
  deleteLink: [linkId: string];
  deleteEntity: [entityId: string];
}>();

// ── Relation selector popup (shown after drag-to-connect) ──────────────────
const relSelector = ref<{ x: number; y: number; sourceId: string; targetId: string } | null>(null);
const selectedRelId = ref('');

// ── Link label edit ─────────────────────────────────────────────────────────
const editingLink = ref<{ id: string; label: string } | null>(null);

// ── Context menu for edges ──────────────────────────────────────────────────
const contextMenu = ref<{ x: number; y: number; linkId: string; label: string } | null>(null);

const containerRef = ref<HTMLElement | null>(null);
let cy: Core | null = null;
let dragSourceId: string | null = null;

// ── Class color palette ─────────────────────────────────────────────────────
const CLASS_COLORS: string[] = [
  '#DBEAFE', '#D1FAE5', '#FEF3C7', '#FCE7F3', '#EDE9FE', '#FFEDD5',
];
function classColor(classId: string): string {
  const idx = props.classes.findIndex(c => c.id === classId);
  return CLASS_COLORS[idx % CLASS_COLORS.length] ?? '#F3F4F6';
}

function classNameForEntity(entity: OFEntity): string {
  return props.classes.find(c => c.id === entity.class_id)?.name ?? '?';
}

function entityLabel(entity: OFEntity): string {
  const first = Object.entries(entity.properties).find(([, v]) => v !== null && v !== '');
  const className = classNameForEntity(entity);
  return first ? `${className}: ${first[1]}` : className;
}

// ── Build Cytoscape elements from props ─────────────────────────────────────
function buildElements() {
  const nodes = props.entities.map(e => ({
    group: 'nodes' as const,
    data: {
      id: e.id,
      label: entityLabel(e),
      classId: e.class_id,
      color: classColor(e.class_id),
    },
  }));
  const edges = props.links.map(l => ({
    group: 'edges' as const,
    data: {
      id: l.id,
      source: l.source_entity_id,
      target: l.target_entity_id,
      label: l.label,
      linkId: l.id,
    },
  }));
  return [...nodes, ...edges];
}

function initCy() {
  if (!containerRef.value) return;
  cy = cytoscape({
    container: containerRef.value,
    elements: buildElements(),
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'border-color': '#0066CC',
          'border-width': 1.5,
          label: 'data(label)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'font-size': 11,
          'font-family': 'Inter, sans-serif',
          width: 32,
          height: 32,
          shape: 'ellipse',
        },
      },
      {
        selector: 'node:selected',
        style: { 'border-color': '#0066CC', 'border-width': 3, 'z-index': 10 },
      },
      {
        selector: 'node:active',
        style: { 'overlay-opacity': 0 },
      },
      {
        selector: 'edge',
        style: {
          width: 2,
          'line-color': '#0066CC',
          'target-arrow-color': '#0066CC',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          label: 'data(label)',
          'font-size': 11,
          'font-family': 'Inter Mono, monospace',
          'text-rotation': 'autorotate',
          'text-margin-y': -8,
          color: '#333',
        },
      },
      {
        selector: 'edge:selected',
        style: { 'line-color': '#0044AA', width: 3, 'text-background-color': '#E0F0FF', 'text-background-opacity': 1 },
      },
      {
        selector: 'edge:hover',
        style: { 'line-color': '#0044AA', width: 3 },
      },
    ],
    layout: { name: 'cose', animate: false, padding: 40 },
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
  });

  // ── Drag-to-connect ────────────────────────────────────────────────────────
  cy.on('mousedown', 'node', (evt) => {
    dragSourceId = evt.target.id() as string;
  });

  cy.on('mouseup', 'node', (evt) => {
    const targetId = evt.target.id() as string;
    if (dragSourceId && dragSourceId !== targetId) {
      const renderedPos = evt.renderedPosition;
      relSelector.value = {
        x: renderedPos.x,
        y: renderedPos.y,
        sourceId: dragSourceId,
        targetId,
      };
      selectedRelId.value = '';
    }
    dragSourceId = null;
  });

  cy.on('mouseup', (evt) => {
    if (evt.target === cy) dragSourceId = null;
  });

  // ── Right-click on edge ────────────────────────────────────────────────────
  cy.on('cxttap', 'edge', (evt) => {
    evt.originalEvent.preventDefault();
    const edge = evt.target;
    const pos = evt.renderedPosition;
    contextMenu.value = {
      x: pos.x,
      y: pos.y,
      linkId: edge.data('linkId') as string,
      label: edge.data('label') as string,
    };
  });

  // ── Click on canvas — close popups ────────────────────────────────────────
  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      relSelector.value = null;
      contextMenu.value = null;
    }
  });
}

// ── Sync data changes to Cytoscape ──────────────────────────────────────────
function syncToCy() {
  if (!cy) return;
  const desired = buildElements();

  // Remove stale elements
  const desiredIds = new Set(desired.map(e => e.data.id));
  cy.elements().filter(el => !desiredIds.has(el.id())).remove();

  // Add / update
  for (const el of desired) {
    const existing = cy.getElementById(el.data.id);
    if (existing.length === 0) {
      cy.add(el);
    } else {
      existing.data(el.data);
    }
  }

  // Re-run layout only when nodes changed
  const nodeCount = cy.nodes().length;
  if (nodeCount > 0 && nodeCount !== _lastNodeCount) {
    cy.layout({ name: 'cose', animate: false, padding: 40 }).run();
    _lastNodeCount = nodeCount;
  }
}
let _lastNodeCount = 0;

watch([() => props.entities, () => props.links], () => {
  nextTick(syncToCy);
}, { deep: true });

onMounted(() => {
  nextTick(initCy);
});
onBeforeUnmount(() => { cy?.destroy(); });

// ── Zoom controls ────────────────────────────────────────────────────────────
function zoomIn() { cy?.zoom({ level: (cy.zoom() * 1.2), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }); }
function zoomOut() { cy?.zoom({ level: (cy.zoom() / 1.2), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }); }

// ── Confirm relation from selector ──────────────────────────────────────────
function confirmRelation() {
  if (!relSelector.value || !selectedRelId.value) return;
  emit('createLink', relSelector.value.sourceId, relSelector.value.targetId, selectedRelId.value);
  relSelector.value = null;
}

// ── Link label edit ──────────────────────────────────────────────────────────
function startEditLabel(linkId: string, currentLabel: string) {
  editingLink.value = { id: linkId, label: currentLabel };
  contextMenu.value = null;
}

function commitLabelEdit() {
  if (editingLink.value) {
    emit('patchLinkLabel', editingLink.value.id, editingLink.value.label);
  }
  editingLink.value = null;
}

// ── Export PNG ───────────────────────────────────────────────────────────────
function exportPng() {
  if (!cy) return;
  const png = cy.png({ full: true, scale: 2 });
  const a = document.createElement('a');
  const d = new Date();
  const ds = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
  a.href = png;
  a.download = `graph_${ds}.png`;
  a.click();
}

defineExpose({ exportPng });
</script>

<template>
  <div class="of-workspace">
    <!-- Cytoscape canvas -->
    <div ref="containerRef" class="of-cy-container" />

    <!-- Zoom controls (bottom-right) -->
    <div class="of-zoom-controls">
      <button class="of-btn of-btn--icon" @click="zoomIn">＋</button>
      <button class="of-btn of-btn--icon" @click="zoomOut">－</button>
    </div>

    <!-- Relation selector popup -->
    <div
      v-if="relSelector"
      class="of-popup"
      :style="{ left: relSelector.x + 'px', top: relSelector.y + 'px' }"
    >
      <p class="of-popup__title">选择关系类型</p>
      <select v-model="selectedRelId" class="of-input" style="min-width:160px">
        <option value="">— 选择关系 —</option>
        <option v-for="rel in relations" :key="rel.id" :value="rel.id">{{ rel.name }}</option>
      </select>
      <button class="of-btn of-btn--primary" style="margin-top:8px;width:100%" :disabled="!selectedRelId" @click="confirmRelation">Confirm</button>
    </div>

    <!-- Edge context menu -->
    <ul
      v-if="contextMenu"
      class="of-context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <li @click="startEditLabel(contextMenu.linkId, contextMenu.label)">Edit Label</li>
      <li>Copy</li>
      <li class="of-menu__danger" @click="emit('deleteLink', contextMenu.linkId); contextMenu = null">🗑️ Delete</li>
    </ul>

    <!-- Link label inline editor -->
    <div v-if="editingLink" class="of-label-editor">
      <input
        v-model="editingLink.label"
        class="of-input"
        style="width:120px;height:24px;font-size:12px"
        @keyup.enter="commitLabelEdit"
        @blur="commitLabelEdit"
        autofocus
      />
    </div>
  </div>
</template>
