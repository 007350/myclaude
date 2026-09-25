from .registry import registry
from ..core import default_skill_manager


@registry.register(
    name="activate_skill",
    description="按需激活并载入专业领域技能（Skill）的完整执行指南与配套脚本说明。当用户任务涉及特定专业规范（如测试、工作流、特定架构等）时调用。"
)
def activate_skill(skill_name: str) -> str:
    """按需激活指定技能并返回其详细操作规范与配套脚本路径"""
    if not skill_name or not skill_name.strip():
        return "错误: 请提供需要激活的技能名称 (skill_name)。"

    ok, content = default_skill_manager.activate_skill(skill_name.strip())
    return content
