import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiGet, apiPost, apiDelete, apiPatch } from '@/api/client';
import type {
  OFOntology,
  OFGraph,
  OFClass,
  OFRelation,
  OFEntity,
  OFLink,
} from '@/types';

export function useOntoFlowStore() {
  return defineStore('ontoflow', () => {
    const ontology = ref<OFOntology>({ classes: [], relations: [] });
    const graph = ref<OFGraph>({ entities: [], links: [] });
    const loading = ref(false);
    const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null);

    let _saveTimer: ReturnType<typeof setTimeout> | null = null;

    function showToast(message: string, type: 'success' | 'error' = 'success') {
      toast.value = { message, type };
      setTimeout(() => { toast.value = null; }, 3000);
    }

    function scheduleSave() {
      if (_saveTimer) clearTimeout(_saveTimer);
      _saveTimer = setTimeout(async () => {
        try {
          await apiPost('/api/ontoflow/save', {});
          showToast('数据已保存');
        } catch {
          // silent — auto-save failures don't interrupt the user
        }
      }, 500);
    }

    async function loadOntology() {
      loading.value = true;
      try {
        ontology.value = await apiGet<OFOntology>('/api/ontoflow/ontology');
      } catch (e) {
        showToast(e instanceof Error ? e.message : '加载本体失败', 'error');
      } finally {
        loading.value = false;
      }
    }

    async function loadGraph() {
      loading.value = true;
      try {
        graph.value = await apiGet<OFGraph>('/api/ontoflow/graph');
      } catch (e) {
        showToast(e instanceof Error ? e.message : '加载图谱失败', 'error');
      } finally {
        loading.value = false;
      }
    }

    async function loadAll() {
      await Promise.all([loadOntology(), loadGraph()]);
    }

    // ── Classes ──────────────────────────────────────────────────────────────

    async function createClass(name: string, description: string): Promise<OFClass | null> {
      try {
        const cls = await apiPost<OFClass>('/api/ontoflow/classes', { name, description });
        ontology.value.classes.push(cls);
        scheduleSave();
        return cls;
      } catch (e) {
        showToast(e instanceof Error ? e.message : '创建类失败', 'error');
        return null;
      }
    }

    async function deleteClass(classId: string) {
      try {
        await apiDelete(`/api/ontoflow/classes/${classId}`);
        ontology.value.classes = ontology.value.classes.filter(c => c.id !== classId);
        ontology.value.relations = ontology.value.relations.filter(
          r => r.source_class_id !== classId && r.target_class_id !== classId
        );
        const removedEntityIds = graph.value.entities
          .filter(e => e.class_id === classId)
          .map(e => e.id);
        graph.value.entities = graph.value.entities.filter(e => e.class_id !== classId);
        graph.value.links = graph.value.links.filter(
          l => !removedEntityIds.includes(l.source_entity_id) && !removedEntityIds.includes(l.target_entity_id)
        );
        scheduleSave();
      } catch (e) {
        showToast(e instanceof Error ? e.message : '删除类失败', 'error');
      }
    }

    // ── Properties ───────────────────────────────────────────────────────────

    async function addProperty(classId: string, name: string, type: 'string' | 'number', unique: boolean) {
      try {
        const prop = await apiPost(`/api/ontoflow/classes/${classId}/properties`, { name, type, unique });
        const cls = ontology.value.classes.find(c => c.id === classId);
        if (cls) cls.properties.push(prop as OFClass['properties'][0]);
        scheduleSave();
        return prop;
      } catch (e) {
        showToast(e instanceof Error ? e.message : '添加属性失败', 'error');
        return null;
      }
    }

    async function deleteProperty(classId: string, propId: string) {
      try {
        await apiDelete(`/api/ontoflow/classes/${classId}/properties/${propId}`);
        const cls = ontology.value.classes.find(c => c.id === classId);
        if (cls) cls.properties = cls.properties.filter(p => p.id !== propId);
        scheduleSave();
      } catch (e) {
        showToast(e instanceof Error ? e.message : '删除属性失败', 'error');
      }
    }

    // ── Relations ────────────────────────────────────────────────────────────

    async function createRelation(
      name: string,
      sourceClassId: string,
      targetClassId: string,
      description: string
    ): Promise<OFRelation | null> {
      try {
        const rel = await apiPost<OFRelation>('/api/ontoflow/relations', {
          name,
          source_class_id: sourceClassId,
          target_class_id: targetClassId,
          description,
        });
        ontology.value.relations.push(rel);
        scheduleSave();
        return rel;
      } catch (e) {
        showToast(e instanceof Error ? e.message : '创建关系失败', 'error');
        return null;
      }
    }

    async function deleteRelation(relationId: string) {
      try {
        await apiDelete(`/api/ontoflow/relations/${relationId}`);
        ontology.value.relations = ontology.value.relations.filter(r => r.id !== relationId);
        graph.value.links = graph.value.links.filter(l => l.relation_id !== relationId);
        scheduleSave();
      } catch (e) {
        showToast(e instanceof Error ? e.message : '删除关系失败', 'error');
      }
    }

    // ── Entities ─────────────────────────────────────────────────────────────

    async function createEntity(
      classId: string,
      properties: Record<string, string | number | boolean | null>
    ): Promise<OFEntity | null> {
      try {
        const entity = await apiPost<OFEntity>('/api/ontoflow/entities', {
          class_id: classId,
          properties,
        });
        graph.value.entities.push(entity);
        scheduleSave();
        return entity;
      } catch (e) {
        showToast(e instanceof Error ? e.message : '创建实体失败', 'error');
        return null;
      }
    }

    async function deleteEntity(entityId: string) {
      try {
        await apiDelete(`/api/ontoflow/entities/${entityId}`);
        graph.value.entities = graph.value.entities.filter(e => e.id !== entityId);
        graph.value.links = graph.value.links.filter(
          l => l.source_entity_id !== entityId && l.target_entity_id !== entityId
        );
        scheduleSave();
      } catch (e) {
        showToast(e instanceof Error ? e.message : '删除实体失败', 'error');
      }
    }

    // ── Links ────────────────────────────────────────────────────────────────

    async function createLink(
      sourceEntityId: string,
      targetEntityId: string,
      relationId: string
    ): Promise<OFLink | null> {
      try {
        const link = await apiPost<OFLink>('/api/ontoflow/links', {
          source_entity_id: sourceEntityId,
          target_entity_id: targetEntityId,
          relation_id: relationId,
        });
        graph.value.links.push(link);
        scheduleSave();
        return link;
      } catch (e) {
        showToast(e instanceof Error ? e.message : '关系类型不兼容', 'error');
        return null;
      }
    }

    async function patchLinkLabel(linkId: string, label: string) {
      try {
        const updated = await apiPatch<OFLink>(`/api/ontoflow/links/${linkId}/label`, { label });
        const link = graph.value.links.find(l => l.id === linkId);
        if (link) link.label = updated.label;
        scheduleSave();
      } catch (e) {
        showToast(e instanceof Error ? e.message : '修改标签失败', 'error');
      }
    }

    async function deleteLink(linkId: string) {
      try {
        await apiDelete(`/api/ontoflow/links/${linkId}`);
        graph.value.links = graph.value.links.filter(l => l.id !== linkId);
        scheduleSave();
      } catch (e) {
        showToast(e instanceof Error ? e.message : '删除关系失败', 'error');
      }
    }

    // ── CSV ──────────────────────────────────────────────────────────────────

    async function importCsv(file: File, classId: string): Promise<{ imported: number; matched_columns: string[] } | null> {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:18080';
        const res = await fetch(`${API_BASE}/api/ontoflow/import/csv?class_id=${encodeURIComponent(classId)}`, {
          method: 'POST',
          body: formData,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: '导入失败' }));
          throw new Error((err as { detail: string }).detail);
        }
        const result = await res.json() as { imported: number; matched_columns: string[] };
        showToast(`成功导入 ${result.imported} 个实体`);
        await loadGraph();
        scheduleSave();
        return result;
      } catch (e) {
        showToast(e instanceof Error ? e.message : '导入失败', 'error');
        return null;
      }
    }

    return {
      ontology,
      graph,
      loading,
      toast,
      loadAll,
      loadOntology,
      loadGraph,
      createClass,
      deleteClass,
      addProperty,
      deleteProperty,
      createRelation,
      deleteRelation,
      createEntity,
      deleteEntity,
      createLink,
      patchLinkLabel,
      deleteLink,
      importCsv,
      showToast,
    };
  })();
}
