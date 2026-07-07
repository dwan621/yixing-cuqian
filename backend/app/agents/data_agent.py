"""
Data Agent (F2-4 数据模拟).

角色定义: emit industry-appropriate mock data (JSON tables + CSV rendering) for the demo.
输入格式: ctx.outputs["parse"], ctx.outputs["design"]
输出格式: MockDataPack + ctx.outputs["data"]
约束条件:
  - Use the industry template's mock_data_schema verbatim (no fabricated fields).
  - Every table has >= 3 rows (AC-4).
  - CSV is UTF-8, header from the first row's keys.
"""
from __future__ import annotations
import csv
import io
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates


class MockDataPack(BaseModel):
    tables: dict[str, list[dict]]
    csv_by_table: dict[str, str]


def _rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


class DataAgent:
    name = "data"

    async def run(self, ctx: AgentContext) -> MockDataPack:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)
        tmpl = load_templates()[parsed.industry_key]
        tables = {name: list(rows) for name, rows in tmpl.mock_data_schema.items()}
        csv_by_table = {name: _rows_to_csv(rows) for name, rows in tables.items()}
        pack = MockDataPack(tables=tables, csv_by_table=csv_by_table)
        ctx.outputs[self.name] = pack.model_dump()
        return pack
