<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useOntoFlowStore } from '@/stores/useOntoFlowStore';
import OntologyPanel from '@/components/ontoflow/OntologyPanel.vue';
import GraphWorkspace from '@/components/ontoflow/GraphWorkspace.vue';
import CreateClassModal from '@/components/ontoflow/CreateClassModal.vue';
import AddRelationModal from '@/components/ontoflow/AddRelationModal.vue';
import CreateEntityModal from '@/components/ontoflow/CreateEntityModal.vue';
import CsvImportModal from '@/components/ontoflow/CsvImportModal.vue';

const store = useOntoFlowStore();
const workspaceRef = ref<InstanceType<typeof GraphWorkspace> | null>(null);

// ── Modal visibility ──────────────────────────────────────────────────────────
const showCreateClass = ref(false);
const showAddRelation = ref(false);
const showCreateEntity = ref(false);
const showCsvImport = ref(false);
const showExportMenu = ref(false);

// ── Init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await store.loadAll();
  window.addEventListener('beforeunload', handleBeforeUnload);
});
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload);
});

function handleBeforeUnload() {
  // Flush pending auto-save synchronously via localStorage snapshot
  localStorage.setItem('ontoflow_dirty', 'true');
}

// ── Toolbar actions ───────────────────────────────────────────────────────────
async function doExport(format: 'turtle' | 'jsonld') {
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:18080';
  const endpoint = format === 'turtle' ? '/api/ontoflow/export/turtle' : '/api/ontoflow/export/jsonld';
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '导出失败' })) as { detail: string };
    store.showToast(err.detail, 'error');
    return;
  }
  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') ?? '';
  const fname = cd.match(/filename="([^"]+)"/)?.[1] ?? `ontology.${format === 'turtle' ? 'ttl' : 'jsonld'}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fname;
  a.click();
  URL.revokeObjectURL(url);
  showExportMenu.value = false;
}

async function exportCsv() {
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:18080';
  const res = await fetch(`${API_BASE}/api/ontoflow/export/csv`);
  if (!res.ok) {
    store.showToast('导出失败', 'error');
    return;
  }
  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') ?? '';
  const fname = cd.match(/filename="([^"]+)"/)?.[1] ?? 'entities.csv';
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fname;
  a.click();
  URL.revokeObjectURL(url);
}

// ── OntologyPanel events ──────────────────────────────────────────────────────
function onAddProperty(classId: string, name: string, type: 'string' | 'number', unique: boolean) {
  store.addProperty(classId, name, type, unique);
}

// ── GraphWorkspace events ─────────────────────────────────────────────────────
async function onCreateLink(sourceId: string, targetId: string, relationId: string) {
  await store.createLink(sourceId, targetId, relationId);
}
</script>

<template>
  <div class="of-root" @click.capture="showExportMenu = false">
    <!-- ── Toolbar ─────────────────────────────────────────────────────────── -->
    <header class="of-toolbar">
      <span class="of-toolbar__logo">OntoFlow Basic</span>

      <div class="of-toolbar__actions">
        <!-- Graph area buttons -->
        <button class="of-btn of-btn--primary" @click="showCreateEntity = true">＋ Create Entity</button>
        <button class="of-btn of-btn--ghost" title="Import Entities" @click="showCsvImport = true">📤 Import CSV</button>
        <button class="of-btn of-btn--ghost" title="Export Entities" @click="exportCsv">📥 Export CSV</button>
        <button class="of-btn of-btn--ghost" title="Export as PNG" @click="workspaceRef?.exportPng()">🖼️ Export PNG</button>

        <!-- Export ontology dropdown -->
        <div class="of-export-wrap" @click.stop>
          <button class="of-btn of-btn--ghost" @click="showExportMenu = !showExportMenu">
            ⬇️ Export <span style="font-size:10px">▾</span>
          </button>
          <ul v-if="showExportMenu" class="of-menu of-menu--below">
            <li @click="doExport('turtle')">RDF Turtle</li>
            <li @click="doExport('jsonld')">JSON-LD</li>
          </ul>
        </div>
      </div>
    </header>

    <!-- ── Body ──────────────────────────────────────────────────────────────── -->
    <div class="of-body">
      <!-- Left sidebar -->
      <OntologyPanel
        :classes="store.ontology.classes"
        :relations="store.ontology.relations"
        @add-class="showCreateClass = true"
        @delete-class="store.deleteClass"
        @add-property="onAddProperty"
        @delete-property="store.deleteProperty"
        @add-relation="showAddRelation = true"
        @delete-relation="store.deleteRelation"
      />

      <!-- Right graph workspace -->
      <GraphWorkspace
        ref="workspaceRef"
        :classes="store.ontology.classes"
        :relations="store.ontology.relations"
        :entities="store.graph.entities"
        :links="store.graph.links"
        @create-link="onCreateLink"
        @patch-link-label="store.patchLinkLabel"
        @delete-link="store.deleteLink"
        @delete-entity="store.deleteEntity"
      />
    </div>

    <!-- ── Toast ─────────────────────────────────────────────────────────────── -->
    <transition name="of-toast-fade">
      <div
        v-if="store.toast"
        class="of-toast"
        :class="store.toast.type === 'error' ? 'of-toast--error' : 'of-toast--success'"
        @click="store.toast = null"
      >
        {{ store.toast.message }}
      </div>
    </transition>

    <!-- ── Modals ─────────────────────────────────────────────────────────────── -->
    <CreateClassModal
      v-if="showCreateClass"
      :existing-names="store.ontology.classes.map(c => c.name)"
      @confirm="(n, d) => { store.createClass(n, d); showCreateClass = false; }"
      @cancel="showCreateClass = false"
    />

    <AddRelationModal
      v-if="showAddRelation"
      :classes="store.ontology.classes"
      :existing-names="store.ontology.relations.map(r => r.name)"
      @confirm="(n, s, t, d) => { store.createRelation(n, s, t, d); showAddRelation = false; }"
      @cancel="showAddRelation = false"
    />

    <CreateEntityModal
      v-if="showCreateEntity"
      :classes="store.ontology.classes"
      @confirm="(cid, props) => { store.createEntity(cid, props); showCreateEntity = false; }"
      @cancel="showCreateEntity = false"
    />

    <CsvImportModal
      v-if="showCsvImport"
      :classes="store.ontology.classes"
      @confirm="(f, cid) => { store.importCsv(f, cid); showCsvImport = false; }"
      @cancel="showCsvImport = false"
    />
  </div>
</template>

<style scoped>
.of-root { display:flex; flex-direction:column; height:100vh; background:#F8F9FA; font-family:Inter,sans-serif; }
.of-toolbar {
  height:64px; background:#fff; box-shadow:0 1px 0 #e0e0e0;
  display:flex; align-items:center; padding:0 24px; gap:12px; flex-shrink:0;
}
.of-toolbar__logo { font-weight:700; font-size:18px; color:#111; margin-right:auto; }
.of-toolbar__actions { display:flex; align-items:center; gap:8px; }
.of-body { display:flex; flex:1; overflow:hidden; }
.of-export-wrap { position:relative; }
</style>

<style>
/* ── Global OntoFlow design tokens ── */
:root {
  --of-primary: #0066CC;
  --of-success: #4CAF50;
  --of-error: #F44336;
  --of-bg: #F8F9FA;
  --of-border: #E0E0E0;
  --of-radius: 4px;
}

/* Buttons */
.of-btn {
  border:none; cursor:pointer; border-radius:var(--of-radius);
  font-size:13px; font-family:Inter,sans-serif;
  padding:6px 14px; transition:box-shadow .15s;
}
.of-btn:hover { box-shadow:0 2px 8px rgba(0,0,0,.1); }
.of-btn:disabled { opacity:.5; cursor:not-allowed; }
.of-btn--primary { background:var(--of-primary); color:#fff; }
.of-btn--ghost { background:#f0f0f0; color:#333; }
.of-btn--icon { padding:4px 8px; background:transparent; font-size:16px; }
.of-btn--sm { font-size:12px; padding:2px 6px; }
.of-btn--xs { font-size:11px; padding:1px 5px; }
.of-btn--danger { color:var(--of-error); }

/* Inputs */
.of-input {
  width:100%; height:40px; border:1px solid var(--of-border);
  border-radius:var(--of-radius); padding:0 10px; font-size:13px;
  font-family:Inter,sans-serif; outline:none; box-sizing:border-box;
}
.of-input:focus { border-color:var(--of-primary); }
.of-input--error { border-color:var(--of-error); }
.of-textarea { height:80px; resize:vertical; padding:8px 10px; }

/* Modals */
.of-modal-overlay {
  position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:200;
  display:flex; align-items:center; justify-content:center;
}
.of-modal {
  background:#fff; border-radius:8px; padding:24px; box-shadow:0 8px 32px rgba(0,0,0,.2);
}
.of-modal__title { margin:0 0 16px; font-size:16px; font-weight:700; }
.of-modal__actions { display:flex; justify-content:flex-end; gap:8px; margin-top:20px; }
.of-field { margin-bottom:12px; }
.of-field--row { display:flex; align-items:center; gap:12px; }
.of-label { display:block; font-size:13px; color:#444; margin-bottom:4px; font-weight:500; }
.of-required { color:var(--of-error); }
.of-error { font-size:12px; color:var(--of-error); margin-top:4px; }
.of-hint { font-size:12px; color:#888; margin-top:4px; }

/* Toggle */
.of-toggle {
  border:1px solid var(--of-border); border-radius:12px; padding:3px 10px;
  font-size:12px; cursor:pointer; background:#f0f0f0; transition:background .15s;
}
.of-toggle--on { background:var(--of-primary); color:#fff; border-color:var(--of-primary); }

/* Panel */
.of-panel {
  width:250px; flex-shrink:0; background:#fff; border-right:1px solid var(--of-border);
  overflow-y:auto; padding:12px;
}
.of-panel__section-header { display:flex; align-items:center; gap:6px; margin-bottom:8px; }
.of-panel__section-title { font-size:12px; font-weight:600; color:#666; text-transform:uppercase; letter-spacing:.5px; flex:1; }

/* Class cards */
.of-class-list { display:flex; flex-direction:column; gap:8px; }
.of-class-card { background:#F0F7FF; border-radius:var(--of-radius); padding:8px 10px; }
.of-class-card__header { display:flex; align-items:center; gap:4px; }
.of-class-card__name { font-weight:600; font-size:13px; flex:1; }
.of-class-card__count { font-size:11px; color:#888; }
.of-class-card__desc { font-size:11px; color:#666; margin:4px 0 0; }
.of-prop-list { list-style:none; margin:4px 0 0; padding:0; }
.of-prop-item { display:flex; align-items:center; gap:4px; font-size:12px; padding:2px 0; }
.of-prop-item__name { font-weight:500; }
.of-prop-item__meta { color:#888; font-size:11px; flex:1; }
.of-empty { font-size:12px; color:#bbb; padding:4px 0; }

/* Relations */
.of-rel-list { list-style:none; padding:0; margin:0; }
.of-rel-item { display:flex; align-items:center; gap:4px; font-size:12px; padding:4px 0; border-bottom:1px solid #f0f0f0; }
.of-rel-item span { flex:1; }

/* Menus */
.of-menu-wrapper { position:relative; }
.of-menu {
  position:absolute; right:0; top:100%; background:#fff; border:1px solid var(--of-border);
  border-radius:var(--of-radius); box-shadow:0 4px 12px rgba(0,0,0,.1);
  list-style:none; margin:2px 0 0; padding:4px 0; z-index:100; min-width:140px;
}
.of-menu li { padding:8px 14px; font-size:13px; cursor:pointer; }
.of-menu li:hover { background:#f5f5f5; }
.of-menu__danger { color:var(--of-error); }
.of-menu--below { top:100%; left:0; right:auto; }

/* Context menu */
.of-context-menu {
  position:absolute; background:#fff; border:1px solid var(--of-border);
  border-radius:var(--of-radius); box-shadow:0 4px 12px rgba(0,0,0,.15);
  list-style:none; padding:4px 0; z-index:150; min-width:130px;
}
.of-context-menu li { padding:8px 14px; font-size:13px; cursor:pointer; }
.of-context-menu li:hover { background:#f5f5f5; }

/* Graph workspace */
.of-workspace { flex:1; position:relative; overflow:hidden; }
.of-cy-container { width:100%; height:100%; }
.of-zoom-controls {
  position:absolute; bottom:20px; right:20px;
  display:flex; flex-direction:column; gap:4px;
}
.of-zoom-controls .of-btn { background:#F0F0F0; border:1px solid var(--of-border); width:32px; height:32px; padding:0; border-radius:var(--of-radius); }

/* Popup (relation selector) */
.of-popup {
  position:absolute; background:#fff; border:1px solid var(--of-border);
  border-radius:8px; box-shadow:0 4px 16px rgba(0,0,0,.15);
  padding:12px; z-index:120; min-width:180px;
}
.of-popup__title { font-size:12px; font-weight:600; margin:0 0 8px; }

/* Label editor */
.of-label-editor {
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  z-index:130; background:#fff; border:1px solid var(--of-primary);
  border-radius:var(--of-radius); padding:4px;
}

/* CSV match table */
.of-match-table { border:1px solid var(--of-border); border-radius:var(--of-radius); overflow:hidden; margin-top:8px; }
.of-match-table__header, .of-match-table__row { display:grid; grid-template-columns:1fr 1fr 48px; gap:0; }
.of-match-table__header { background:#f5f5f5; font-size:12px; font-weight:600; padding:6px 10px; }
.of-match-table__row { padding:5px 10px; font-size:12px; border-top:1px solid #f0f0f0; }
.of-match--ok { color:var(--of-success); }
.of-match--warn { color:orange; }

/* Toast */
.of-toast {
  position:fixed; top:24px; right:24px; padding:10px 18px;
  border-radius:6px; font-size:13px; z-index:300; cursor:pointer;
  box-shadow:0 4px 12px rgba(0,0,0,.15);
}
.of-toast--success { background:#fff; border:1px solid var(--of-success); color:#2e7d32; }
.of-toast--error { background:#fff; border:1px solid var(--of-error); color:#c62828; }
.of-toast-fade-enter-active, .of-toast-fade-leave-active { transition:opacity .3s; }
.of-toast-fade-enter-from, .of-toast-fade-leave-to { opacity:0; }
</style>
