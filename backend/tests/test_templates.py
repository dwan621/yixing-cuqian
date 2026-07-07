from app.templates import load_templates, resolve_industry, IndustryTemplate


def test_load_templates_finds_all_three_seeded_industries():
    templates = load_templates()
    names = set(templates.keys())
    assert {"manufacturing", "finance", "retail"} <= names


def test_manufacturing_has_scenario_and_feature_bank():
    t = load_templates()["manufacturing"]
    assert isinstance(t, IndustryTemplate)
    assert "供应链管理" in t.default_scenarios
    assert len(t.feature_bank) >= 5  # AC-3 needs >= 3; we ship >= 5 per industry


def test_resolve_industry_matches_by_alias():
    templates = load_templates()
    t = resolve_industry("制造业", templates)
    assert t is not None
    assert t.name == "manufacturing"


def test_resolve_industry_case_insensitive():
    templates = load_templates()
    t = resolve_industry("MANUFACTURING", templates)
    assert t is not None
    assert t.name == "manufacturing"


def test_resolve_industry_unknown_returns_none():
    templates = load_templates()
    assert resolve_industry("外星科技", templates) is None


def test_feature_bank_entries_carry_demo_steps_and_talking_points():
    t = load_templates()["manufacturing"]
    for f in t.feature_bank:
        assert f.id
        assert f.title
        assert len(f.demo_steps) >= 1
        assert len(f.talking_points) >= 1


def test_mock_data_schema_lists_at_least_one_table_per_industry():
    for name in ("manufacturing", "finance", "retail"):
        t = load_templates()[name]
        assert len(t.mock_data_schema) >= 1
        # every schema entry describes a list of rows
        for table_name, rows in t.mock_data_schema.items():
            assert isinstance(rows, list) and len(rows) >= 3
