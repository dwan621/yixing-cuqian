"""
Industry template loader.

Prompt-style contract (spec §5.3):
- 角色定义: static configuration for industry-specific 功能库/数据字段/话术
- 输入格式: YAML files under templates/industries/*.yaml
- 输出格式: {lowercase(name) -> IndustryTemplate}, cached on first call
- 约束条件: no I/O outside this loader; no network; no writes
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class FeatureSpec(BaseModel):
    id: str
    title: str
    description: str
    demo_steps: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)


class IndustryTemplate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    default_scenarios: list[str] = Field(default_factory=list)
    feature_bank: list[FeatureSpec]
    mock_data_schema: dict[str, list[dict[str, Any]]]
    talking_points: list[str] = Field(default_factory=list)
    architecture_snippet: str = ""


_INDUSTRIES_DIR = Path(__file__).parent / "industries"


@lru_cache(maxsize=1)
def load_templates() -> dict[str, IndustryTemplate]:
    result: dict[str, IndustryTemplate] = {}
    for yaml_path in sorted(_INDUSTRIES_DIR.glob("*.yaml")):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        tmpl = IndustryTemplate.model_validate(data)
        result[tmpl.name.lower()] = tmpl
    return result


def resolve_industry(
    query: str, templates: dict[str, IndustryTemplate]
) -> IndustryTemplate | None:
    q = query.strip().lower()
    for tmpl in templates.values():
        if tmpl.name.lower() == q:
            return tmpl
        if any(a.lower() == q for a in tmpl.aliases):
            return tmpl
    return None
