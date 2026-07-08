"""Four-section prompt templates (spec §5.3). One builder per agent role."""
from __future__ import annotations
import json
from pydantic import BaseModel


def _build(
    role_name: str,
    role_desc: str,
    input_ctx: str,
    output_model: type[BaseModel],
    extra_constraints: list[str] | None = None,
) -> str:
    schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False, indent=2)
    constraints = [
        "只返回合法 JSON，不要用 ```json ... ``` 包裹",
        "不要添加任何解释性文字",
    ]
    if extra_constraints:
        constraints.extend(extra_constraints)
    parts = [
        f"## 角色定义\n你是以型促签售前演示平台的 {role_name}。{role_desc}",
        f"## 输入格式\n{input_ctx}",
        f"## 输出格式\n请只返回一个 JSON 对象，严格匹配以下 JSON Schema。不要包含 markdown 代码块标记或其他文字：\n{schema}",
        "## 约束条件\n" + "\n".join(f"{i+1}. {c}" for i, c in enumerate(constraints)),
    ]
    return "\n\n".join(parts)


# ─── Parse Agent prompt ───

def parse_prompt(
    industry: str, scenario: str, scale: str,
    demo_minutes: int, background: str | None,
    known_industries: str,
) -> str:
    from app.agents.parse_agent import ParsedRequirement
    input_ctx = (
        f"用户提交的原始需求：\n"
        f"- 行业: {industry}\n"
        f"- 场景: {scenario}\n"
        f"- 规模: {scale}\n"
        f"- 演示时长: {demo_minutes} 分钟\n"
        f"- 补充背景: {background or '（无）'}\n\n"
        f"已知行业列表（name/别名/默认场景）：\n{known_industries}"
    )
    return _build(
        role_name="需求解析专家",
        role_desc="从客户提交的原始输入中提取结构化需求，识别行业、匹配场景、提取背景要点。",
        input_ctx=input_ctx,
        output_model=ParsedRequirement,
        extra_constraints=[
            "industry_key 必须是已知行业列表中的某个 name（小写形式）",
            "如果行业名匹配了某个行业的别名，industry_key 应对应到正确的 name",
            "matched_scenarios 必须包含用户输入的 scenario，并尽可能从 background 文本中提取更多匹配的默认场景",
            "industry_display 保持用户输入的原始值",
            "如果行业完全无法匹配任何已知行业，industry_key 返回 unknown",
        ],
    )


# ─── Design Agent prompt ───

def design_prompt(parsed: dict, feature_bank_json: str) -> str:
    from app.agents.design_agent import DesignedPlan
    input_ctx = (
        f"解析后的需求：\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n\n"
        f"该行业的全部可选功能清单（feature_bank）：\n{feature_bank_json}\n\n"
        f"请从中选择与客户场景最相关的功能，并分配演示时间。"
    )
    return _build(
        role_name="方案设计师",
        role_desc="根据客户需求和行业功能库，选择最适合演示的功能点，规划时间分配。",
        input_ctx=input_ctx,
        output_model=DesignedPlan,
        extra_constraints=[
            f"features 数量 >= 3，尽量多选关联场景的功能",
            "coverage_ratio 是所选 features 中属于 relevant（scenario 匹配）的比例",
            "time_allocation 中每个 slot 的 minutes >= 1，所有 minutes 之和 == demo_minutes",
            "features 按优先度排序（最相关排最前）",
        ],
    )


# ─── Content Agent prompt ───

def content_prompt(parsed: dict, design: dict) -> str:
    from app.agents.content_agent import DemoScript
    input_ctx = (
        f"客户需求：\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n\n"
        f"选定的功能清单和时间分配：\n{json.dumps(design, ensure_ascii=False, indent=2)}\n\n"
        f"请为每个功能生成演示话术：intro（一句话介绍）、flow（演示步骤列表）、value（价值点）、"
        f"talking_points_5min（5分钟精简版话术）、talking_points_15min（15分钟详细版话术）。"
    )
    return _build(
        role_name="售前内容专家",
        role_desc="根据选定的功能清单，为每个功能编写演示话术和操作步骤。使用专业、有说服力的售前语言风格。",
        input_ctx=input_ctx,
        output_model=DemoScript,
        extra_constraints=[
            "opening 开场白要针对具体行业和场景，体现对客户业务的理解",
            "closing 结束语要有推动下一步行动的号召力",
            "每人 briefing 的 flow 至少 2 步",
            "talking_points_5min 用一句话概括，talking_points_15min 包含具体数据或案例",
        ],
    )


# ─── Data Agent prompt ───

def data_prompt(parsed: dict, schema_ref: str) -> str:
    from app.agents.data_agent import MockDataPack
    input_ctx = (
        f"客户需求：\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n\n"
        f"参考的数据表结构（mock_data_schema）：\n{schema_ref}\n\n"
        f"请生成与客户行业和场景匹配的模拟数据。每个表至少生成3行。"
    )
    return _build(
        role_name="数据模拟专家",
        role_desc="根据客户行业和场景，生成逼真的模拟数据，可直接导入原型系统演示。",
        input_ctx=input_ctx,
        output_model=MockDataPack,
        extra_constraints=[
            "每个表至少生成 3 行数据",
            "数据字段语义要符合该行业的典型业务含义",
            "数值要有合理的量级和变化范围",
        ],
    )


# ─── Architecture Agent prompt ───

def architecture_prompt(parsed: dict, snippet: str) -> str:
    from app.agents.architecture_agent import ArchitectureDoc
    input_ctx = (
        f"客户需求：\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n\n"
        f"参考架构片段：\n{snippet}\n\n"
        f"请生成一段架构适配说明和对应的 Mermaid flowchart TD 图。"
    )
    return _build(
        role_name="架构师",
        role_desc="描述系统架构如何适配客户环境，生成 Mermaid 架构图。",
        input_ctx=input_ctx,
        output_model=ArchitectureDoc,
        extra_constraints=[
            "description 需提到客户行业和场景",
            "mermaid 必须是以 flowchart TD 开头的合法 Mermaid 代码",
            "节点数量 4~8 个，节点标签简洁",
        ],
    )


# ─── Integrate Agent prompt ───

def integrate_prompt(parse: dict, design: dict, content: dict, data: dict, architecture: dict) -> str:
    from app.agents.integrate_agent import FinalPlan
    input_ctx = (
        f"需求解析：\n{json.dumps(parse, ensure_ascii=False, indent=2)}\n\n"
        f"方案设计：\n{json.dumps(design, ensure_ascii=False, indent=2)}\n\n"
        f"内容生成：\n{json.dumps(content, ensure_ascii=False, indent=2)}\n\n"
        f"模拟数据：\n{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
        f"架构描述：\n{json.dumps(architecture, ensure_ascii=False, indent=2)}\n\n"
        f"请将以上所有内容整合为一份完整的 Markdown 售前方案文档。"
    )
    return _build(
        role_name="方案整合专家",
        role_desc="将所有 Agent 的输出整合为一份结构完整、排版美观的 Markdown 售前方案。",
        input_ctx=input_ctx,
        output_model=FinalPlan,
        extra_constraints=[
            "markdown 必须包含以下完整章节：# 售前方案、## 客户需求概览、## 系统架构、## 功能演示清单、## 演示话术、## 模拟数据",
            "架构章节应包含 mermaid 代码块",
            "演示话术应包含开场白和结束语",
            "排版清晰、专业，适合直接展示给客户",
        ],
    )
