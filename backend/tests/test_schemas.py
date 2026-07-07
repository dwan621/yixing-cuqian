import pytest
from pydantic import ValidationError
from app.schemas import RequirementInput


def test_requirement_input_accepts_full_form():
    req = RequirementInput(
        industry="制造业",
        scenario="供应链管理",
        scale="500 人以上",
        demo_minutes=15,
        background="客户痛点：库存周转慢",
        template="供应链演示模板",
    )
    assert req.industry == "制造业"
    assert req.demo_minutes == 15


def test_requirement_input_defaults_optional_fields_to_none():
    req = RequirementInput(
        industry="金融",
        scenario="风控",
        scale="1000 人",
        demo_minutes=5,
    )
    assert req.background is None
    assert req.template is None


def test_requirement_input_missing_required_field_raises():
    with pytest.raises(ValidationError):
        RequirementInput(scenario="供应链", scale="500 人", demo_minutes=10)  # missing industry


def test_requirement_input_rejects_non_positive_demo_minutes():
    with pytest.raises(ValidationError):
        RequirementInput(industry="制造业", scenario="供应链", scale="500 人", demo_minutes=0)


def test_requirement_input_rejects_negative_demo_minutes():
    with pytest.raises(ValidationError):
        RequirementInput(industry="制造业", scenario="供应链", scale="500 人", demo_minutes=-1)
