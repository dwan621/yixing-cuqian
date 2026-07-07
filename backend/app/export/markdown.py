"""Pure rendering: agent outputs -> Markdown pre-sales package."""
from __future__ import annotations
import json


def render_markdown(parse: dict, design: dict, content: dict, data: dict, architecture: dict) -> str:
    lines: list[str] = []
    lines.append("# 售前方案")
    lines.append("")
    # Overview
    lines.append("## 客户需求概览")
    lines.append("")
    lines.append(f"- 行业：{parse['industry_display']}")
    lines.append(f"- 场景：{parse['scenario']}")
    lines.append(f"- 规模：{parse['scale']}")
    lines.append(f"- 演示时长：{parse['demo_minutes']} 分钟")
    if parse.get("background"):
        lines.append(f"- 客户背景：{parse['background']}")
    lines.append(f"- 场景覆盖：{'、'.join(parse['matched_scenarios'])}")
    lines.append(f"- 功能覆盖率：{design['coverage_ratio']:.0%}")
    lines.append("")

    # Architecture
    arch = architecture
    lines.append("## 系统架构")
    lines.append("")
    lines.append(arch["description"])
    lines.append("")
    lines.append("```mermaid")
    lines.append(arch["mermaid"])
    lines.append("```")
    lines.append("")

    # Feature demo list
    lines.append("## 功能演示清单")
    lines.append("")
    briefs = {b["feature_id"]: b for b in content["briefs"]}
    for slot in design["time_allocation"]:
        fid = slot["feature_id"]
        b = briefs.get(fid, {})
        lines.append(f"### {slot['feature_title']}（建议 {slot['minutes']} 分钟）")
        lines.append("")
        lines.append(f"- **简介**：{b.get('intro','')}")
        lines.append("- **演示步骤**：")
        for step in b.get("flow", []):
            lines.append(f"  1. {step}")
        lines.append(f"- **价值点**：{b.get('value','')}")
        lines.append("")

    # Demo script
    lines.append("## 演示话术")
    lines.append("")
    lines.append(f"**开场白**：{content['opening']}")
    lines.append("")
    lines.append("**分功能话术（5 分钟 / 15 分钟版）**：")
    for b in content["briefs"]:
        lines.append(f"- **{b['title']}**")
        lines.append(f"  - 5 分钟版：{b['talking_points_5min']}")
        lines.append(f"  - 15 分钟版：{b['talking_points_15min']}")
    lines.append("")
    lines.append(f"**结束语**：{content['closing']}")
    lines.append("")

    # Mock data
    lines.append("## 模拟数据")
    lines.append("")
    lines.append("以下数据可直接导入客户演示环境。")
    lines.append("")
    for table_name, rows in data["tables"].items():
        lines.append(f"### `{table_name}`")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(rows, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)
