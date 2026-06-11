"""Skill schema and registry tests."""

from __future__ import annotations

import pytest

from skills import (
    BaseSkill,
    SkillAlreadyRegisteredError,
    SkillNotFoundError,
    SkillRegistry,
    SkillRequest,
    SkillResult,
    SkillSpec,
)


class DummySkill(BaseSkill):
    """Simple skill implementation for registry tests."""

    def __init__(self, name: str = "dummy") -> None:
        self._spec = SkillSpec(
            name=name,
            description="Dummy skill for tests",
            input_schema={"text": "str"},
            output_schema={"echo": "str"},
            supported_retriever_types=("keyword",),
            requires_evidence=False,
            supports_async=False,
            tags=("test",),
        )

    @property
    def spec(self) -> SkillSpec:
        return self._spec

    def run(self, request: SkillRequest) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            output={"echo": request.inputs.get("text", "")},
            metadata={"test": True},
        )


def test_skill_request_can_be_created() -> None:
    request = SkillRequest(
        skill_name="dummy",
        inputs={"text": "hello"},
        context={"db_path": "test.db"},
        metadata={"request_id": "r1"},
    )

    assert request.skill_name == "dummy"
    assert request.inputs["text"] == "hello"


def test_skill_request_empty_skill_name_raises() -> None:
    with pytest.raises(ValueError):
        SkillRequest(skill_name="", inputs={})


def test_skill_request_inputs_must_be_dict() -> None:
    with pytest.raises(ValueError):
        SkillRequest(skill_name="dummy", inputs=[])  # type: ignore[arg-type]


@pytest.mark.parametrize("field_name", ["context", "metadata"])
def test_skill_request_optional_maps_must_be_dict(field_name) -> None:
    kwargs = {"skill_name": "dummy", "inputs": {}, field_name: []}

    with pytest.raises(ValueError):
        SkillRequest(**kwargs)  # type: ignore[arg-type]


def test_skill_result_can_be_created() -> None:
    result = SkillResult(skill_name="dummy", output={"ok": True})

    assert result.success is True
    assert result.output["ok"] is True


def test_skill_result_empty_skill_name_raises() -> None:
    with pytest.raises(ValueError):
        SkillResult(skill_name="", output={})


def test_skill_result_output_must_be_dict() -> None:
    with pytest.raises(ValueError):
        SkillResult(skill_name="dummy", output=[])  # type: ignore[arg-type]


def test_skill_result_metadata_must_be_dict() -> None:
    with pytest.raises(ValueError):
        SkillResult(skill_name="dummy", output={}, metadata=[])  # type: ignore[arg-type]


def test_skill_spec_can_be_created() -> None:
    spec = SkillSpec(
        name="dummy",
        description="Dummy skill",
        input_schema={"text": "str"},
        output_schema={"echo": "str"},
        supported_retriever_types=("keyword", "hybrid"),
        tags=["test", "skill"],  # type: ignore[arg-type]
    )

    assert spec.name == "dummy"
    assert spec.supported_retriever_types == ("keyword", "hybrid")
    assert spec.tags == ("test", "skill")


def test_skill_spec_empty_name_raises() -> None:
    with pytest.raises(ValueError):
        SkillSpec(name="", description="Dummy skill")


def test_skill_spec_empty_description_raises() -> None:
    with pytest.raises(ValueError):
        SkillSpec(name="dummy", description="")


def test_skill_spec_empty_supported_retriever_types_raises() -> None:
    with pytest.raises(ValueError):
        SkillSpec(name="dummy", description="Dummy skill", supported_retriever_types=())


def test_skill_spec_unknown_retriever_type_raises() -> None:
    with pytest.raises(ValueError):
        SkillSpec(
            name="dummy",
            description="Dummy skill",
            supported_retriever_types=("keyword", "unknown"),
        )


def test_base_skill_subclass_can_run() -> None:
    skill = DummySkill()
    request = SkillRequest(skill_name="dummy", inputs={"text": "hello"})

    result = skill.run(request)

    assert skill.name == "dummy"
    assert result == SkillResult(
        skill_name="dummy",
        output={"echo": "hello"},
        metadata={"test": True},
    )


def test_skill_registry_register_and_get() -> None:
    registry = SkillRegistry()
    skill = DummySkill()

    registry.register(skill)

    assert registry.get("dummy") is skill


def test_skill_registry_has() -> None:
    registry = SkillRegistry()
    registry.register(DummySkill())

    assert registry.has("dummy") is True
    assert registry.has("missing") is False


def test_skill_registry_list_names_sorted() -> None:
    registry = SkillRegistry()
    registry.register(DummySkill("zeta"))
    registry.register(DummySkill("alpha"))

    assert registry.list_names() == ["alpha", "zeta"]


def test_skill_registry_list_specs_sorted() -> None:
    registry = SkillRegistry()
    registry.register(DummySkill("zeta"))
    registry.register(DummySkill("alpha"))

    assert [spec.name for spec in registry.list_specs()] == ["alpha", "zeta"]


def test_skill_registry_duplicate_name_raises() -> None:
    registry = SkillRegistry()
    registry.register(DummySkill())

    with pytest.raises(SkillAlreadyRegisteredError):
        registry.register(DummySkill())


def test_skill_registry_get_missing_raises() -> None:
    registry = SkillRegistry()

    with pytest.raises(SkillNotFoundError):
        registry.get("missing")


def test_skill_registry_register_non_skill_raises() -> None:
    registry = SkillRegistry()

    with pytest.raises(TypeError):
        registry.register(object())  # type: ignore[arg-type]
