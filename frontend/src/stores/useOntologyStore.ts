import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiGet } from '@/api/client';
import type { ObjectTypePayload, ObjectTypeDefinition, InspectorObjectSchema, InspectorFieldSchema, FieldType } from '@/types';

export function useOntologyStore() {
  return defineStore('ontology', () => {
    // State
    const objectTypes = ref<ObjectTypePayload[]>([]);
    const objectTypeDetails = ref<Map<string, ObjectTypeDefinition>>(new Map());
    const selectedTypeUri = ref<string>('');
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Getters
    const selectedType = computed(() => objectTypes.value.find(t => t.type_uri === selectedTypeUri.value) || null);
    const typeCount = computed(() => objectTypes.value.length);
    const typeLabels = computed(() => objectTypes.value.map(t => t.display_name));

    // Get full schema for selected type
    const selectedTypeSchema = computed(() => {
      if (!selectedTypeUri.value) return null;
      return objectTypeDetails.value.get(selectedTypeUri.value) || null;
    });

    // Convert ObjectTypeDefinition to InspectorObjectSchema
    function toInspectorSchema(definition: ObjectTypeDefinition): InspectorObjectSchema {
      const fields: InspectorFieldSchema[] = Object.entries(definition.properties || {}).map(([name, prop]) => {
        const fieldType = mapPropertyTypeToFieldType(prop.type);
        const schema: InspectorFieldSchema = {
          name,
          label: name,
          fieldType,
          required: !prop.immutable,
          readonly: prop.immutable || false,
          defaultValue: prop.default_value,
          options: prop.type === 'enum' ? (prop.validators?.find(v => v.type === 'enum')?.config as unknown as string[]) : undefined,
          validation: prop.validators && prop.validators.length > 0 ? {
            type: prop.validators[0].type,
            config: prop.validators[0].config,
          } : undefined,
        };
        return schema;
      });

      return {
        type_uri: definition.type_uri,
        display_name: definition.display_name,
        fields,
        bound_actions: definition.bound_actions || [],
        access_level: definition.access_control ? 'CONFIDENTIAL' : 'PUBLIC',
      };
    }

    // Map property type string to FieldType union
    function mapPropertyTypeToFieldType(propType: string): FieldType {
      const mapping: Record<string, FieldType> = {
        'string': 'string',
        'integer': 'integer',
        'float': 'float',
        'boolean': 'boolean',
        'coordinate': 'coordinate',
        'entity_ref': 'entity_ref',
        'datetime': 'datetime',
        'soft_link': 'soft_link',
        'derived': 'derived',
        'time_series': 'time_series',
      };
      return mapping[propType] || 'string';
    }

    // Get property schema by name
    function getPropertySchema(typeUri: string, propertyName: string): InspectorFieldSchema | null {
      const definition = objectTypeDetails.value.get(typeUri);
      if (!definition?.properties) return null;

      const prop = definition.properties[propertyName];
      if (!prop) return null;

      const fieldType = mapPropertyTypeToFieldType(prop.type);
      return {
        name: propertyName,
        label: propertyName,
        fieldType,
        required: !prop.immutable,
        readonly: prop.immutable || false,
        defaultValue: prop.default_value,
        options: prop.type === 'enum' ? (prop.validators?.find(v => v.type === 'enum')?.config as unknown as string[]) : undefined,
        validation: prop.validators && prop.validators.length > 0 ? {
          type: prop.validators[0].type,
          config: prop.validators[0].config,
        } : undefined,
      };
    }

    // Get inspector schema for a type
    function getInspectorSchema(typeUri: string): InspectorObjectSchema | null {
      const definition = objectTypeDetails.value.get(typeUri);
      if (!definition) return null;
      return toInspectorSchema(definition);
    }

    // Get inspector schema for selected type
    function getSelectedInspectorSchema(): InspectorObjectSchema | null {
      if (!selectedTypeUri.value) return null;
      return getInspectorSchema(selectedTypeUri.value);
    }

    // Actions
    async function loadObjectTypes(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const types = await apiGet<ObjectTypePayload[]>('/api/query/object-types');
        objectTypes.value = types;
        if (types.length > 0 && !selectedTypeUri.value) {
          selectedTypeUri.value = types[0].type_uri;
        }
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load object types';
      } finally {
        loading.value = false;
      }
    }

    async function loadFromCommand(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const types = await apiGet<ObjectTypePayload[]>('/api/command/object-types');
        objectTypes.value = types;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load from command';
      } finally {
        loading.value = false;
      }
    }

    // Load full schema detail for a specific type
    async function loadObjectTypeDetail(typeUri: string): Promise<ObjectTypeDefinition | null> {
      loading.value = true;
      error.value = null;
      try {
        const detail = await apiGet<ObjectTypeDefinition>(`/api/query/object-type/${encodeURIComponent(typeUri)}`);
        objectTypeDetails.value.set(typeUri, detail);
        return detail;
      } catch (e) {
        error.value = e instanceof Error ? e.message : `Failed to load type detail: ${typeUri}`;
        return null;
      } finally {
        loading.value = false;
      }
    }

    // Preload all type details
    async function loadAllTypeDetails(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const details = await apiGet<Map<string, ObjectTypeDefinition>>('/api/query/object-types/detail');
        objectTypeDetails.value = new Map(Object.entries(details));
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load all type details';
      } finally {
        loading.value = false;
      }
    }

    function selectType(typeUri: string): void {
      selectedTypeUri.value = typeUri;
      // Auto-load detail if not cached
      if (!objectTypeDetails.value.has(typeUri)) {
        loadObjectTypeDetail(typeUri);
      }
    }

    function clear(): void {
      objectTypes.value = [];
      objectTypeDetails.value.clear();
      selectedTypeUri.value = '';
      error.value = null;
    }

    return {
      objectTypes,
      objectTypeDetails,
      selectedTypeUri,
      selectedType,
      selectedTypeSchema,
      loading,
      error,
      typeCount,
      typeLabels,
      loadObjectTypes,
      loadFromCommand,
      loadObjectTypeDetail,
      loadAllTypeDetails,
      selectType,
      getPropertySchema,
      getInspectorSchema,
      getSelectedInspectorSchema,
      mapPropertyTypeToFieldType,
      toInspectorSchema,
      clear,
    };
  })();
}
