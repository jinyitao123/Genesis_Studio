from __future__ import annotations

import pytest

from backend.ontology.engine import LinkTypeDefinition
from backend.ontology.engine import MigrationPlanRequest
from backend.ontology.engine import ObjectTypeDefinition
from backend.ontology.engine import OTDPropertyDefinition
from backend.ontology.engine import apply_migration_plan
from backend.ontology.engine import generate_migration_plan
from backend.ontology.engine import validate_link_type_definition
from backend.ontology.engine import validate_object_type_definition


class TestObjectTypeDefinition:
    @pytest.mark.unit
    def test_otd_creation_success(self) -> None:
        otd = ObjectTypeDefinition(
            type_uri="com.genesis.test.Drone",
            schema_version="1.0.0",
            display_name="Test Drone",
            parent_type="com.genesis.unit.AirUnit",
            properties=[
                OTDPropertyDefinition(name="battery_level", value_type="float", storage="time_series"),
                OTDPropertyDefinition(name="max_speed", value_type="integer", storage="static"),
            ],
            bound_actions=["ACT_MOVE", "ACT_SELF_DESTRUCT"],
        )

        assert otd.type_uri == "com.genesis.test.Drone"
        assert otd.schema_version == "1.0.0"
        assert len(otd.properties) == 2

    @pytest.mark.unit
    def test_otd_validation_success(self) -> None:
        otd = ObjectTypeDefinition(
            type_uri="com.genesis.test.Vehicle",
            schema_version="1.0.0",
            display_name="Vehicle",
            implements=["IMovable"],
            properties=[
                OTDPropertyDefinition(name="location", value_type="string", storage="computed"),
                OTDPropertyDefinition(name="current_speed", value_type="integer", storage="time_series"),
                OTDPropertyDefinition(name="max_speed", value_type="integer", storage="static"),
            ],
            bound_actions=["ACT_MOVE", "ACT_STOP"],
        )

        result = validate_object_type_definition(otd)

        assert result.valid is True
        assert result.errors == []

    @pytest.mark.unit
    def test_otd_validation_invalid_uri(self) -> None:
        otd = ObjectTypeDefinition(
            type_uri="invalid-uri-format",
            schema_version="1.0.0",
            display_name="Invalid",
            properties=[],
        )

        result = validate_object_type_definition(otd)

        assert result.valid is False
        assert any("type_uri" in error for error in result.errors)

    @pytest.mark.unit
    def test_otd_duplicate_property_names_fail(self) -> None:
        otd = ObjectTypeDefinition(
            type_uri="com.genesis.test.DuplicateProps",
            schema_version="1.0.0",
            display_name="Duplicate Props",
            properties=[
                OTDPropertyDefinition(name="hp", value_type="integer", storage="static"),
                OTDPropertyDefinition(name="hp", value_type="integer", storage="time_series"),
            ],
        )

        result = validate_object_type_definition(otd)

        assert result.valid is False
        assert any("property names must be unique" in error for error in result.errors)


class TestLinkTypeDefinition:
    @pytest.mark.unit
    def test_ltd_creation_success(self) -> None:
        ltd = LinkTypeDefinition(
            link_type_uri="com.genesis.rel.Commands",
            display_name="Command Relation",
            source_type_constraint="Officer",
            target_type_constraint="Unit.*",
            directionality="directed",
            cardinality="ONE_TO_MANY",
        )

        assert ltd.link_type_uri == "com.genesis.rel.Commands"
        assert ltd.cardinality == "ONE_TO_MANY"

    @pytest.mark.unit
    def test_ltd_validation_invalid_one_to_one_constraints(self) -> None:
        ltd = LinkTypeDefinition(
            link_type_uri="com.genesis.rel.Mirror",
            display_name="Mirror",
            source_type_constraint="Unit",
            target_type_constraint="Unit",
            directionality="directed",
            cardinality="ONE_TO_ONE",
        )

        result = validate_link_type_definition(ltd)

        assert result.valid is False
        assert any("ONE_TO_ONE" in error for error in result.errors)


class TestSchemaMigration:
    @pytest.mark.unit
    def test_migration_plan_generation_lazy(self) -> None:
        request = MigrationPlanRequest(
            from_schema_version="1.0.0",
            to_schema_version="1.1.0",
            changed_fields=["name", "description"],
            mode="lazy",
        )

        plan = generate_migration_plan(request)

        assert plan.from_schema_version == "1.0.0"
        assert plan.to_schema_version == "1.1.0"
        assert plan.mode == "lazy"
        assert len(plan.steps) == 4

    @pytest.mark.unit
    def test_migration_plan_breaking_changes_detection(self) -> None:
        request = MigrationPlanRequest(
            from_schema_version="1.0.0",
            to_schema_version="2.0.0",
            changed_fields=["delete", "rename", "new_field"],
            mode="batch",
        )

        plan = generate_migration_plan(request)

        assert "delete" in plan.breaking_changes
        assert "rename" in plan.breaking_changes

    @pytest.mark.unit
    def test_apply_migration_plan_batch_success(self) -> None:
        request = MigrationPlanRequest(
            from_schema_version="1.0.0",
            to_schema_version="1.1.0",
            changed_fields=["new_field"],
            mode="batch",
        )
        plan = generate_migration_plan(request)
        result = apply_migration_plan(plan)

        assert result["success"] is True
        assert result["status"] == "applied"
        assert result["processed_entities"] == 240

    @pytest.mark.unit
    def test_apply_migration_plan_lazy_with_breaking_fails(self) -> None:
        request = MigrationPlanRequest(
            from_schema_version="1.0.0",
            to_schema_version="2.0.0",
            changed_fields=["delete"],
            mode="lazy",
        )
        plan = generate_migration_plan(request)
        result = apply_migration_plan(plan)

        assert result["success"] is False
        assert result["status"] == "failed"
        assert isinstance(result["errors"], list)
        assert len(result["errors"]) > 0
