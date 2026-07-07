import csv
import io
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.data_agent import DataAgent, MockDataPack


async def _prep(industry="制造业"):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry=industry, scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    await DesignAgent().run(ctx)
    return ctx


async def test_data_agent_produces_all_industry_tables():
    ctx = await _prep()
    pack = await DataAgent().run(ctx)
    assert isinstance(pack, MockDataPack)
    # Manufacturing template ships orders, inventory, shipments.
    assert {"orders", "inventory", "shipments"} <= set(pack.tables.keys())


async def test_data_agent_each_table_has_at_least_three_rows():
    ctx = await _prep()
    pack = await DataAgent().run(ctx)
    for name, rows in pack.tables.items():
        assert len(rows) >= 3, f"{name} has < 3 rows"


async def test_data_agent_csv_is_parseable_and_matches_row_count():
    ctx = await _prep()
    pack = await DataAgent().run(ctx)
    for table, csv_str in pack.csv_by_table.items():
        reader = list(csv.DictReader(io.StringIO(csv_str)))
        assert len(reader) == len(pack.tables[table])


async def test_data_agent_industry_fields_match_semantics_finance():
    # Finance table must have transactions with account, amount, risk_score fields.
    ctx = AgentContext(
        session_id="s2",
        requirement=RequirementInput(
            industry="金融", scenario="风控", scale="1000 人", demo_minutes=10
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    await DesignAgent().run(ctx)
    pack = await DataAgent().run(ctx)
    assert "transactions" in pack.tables
    first = pack.tables["transactions"][0]
    for field in ("account", "amount", "risk_score"):
        assert field in first, f"transactions row missing field {field}"


async def test_data_agent_writes_outputs():
    ctx = await _prep()
    await DataAgent().run(ctx)
    assert "data" in ctx.outputs
