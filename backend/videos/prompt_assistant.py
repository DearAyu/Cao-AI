import json
from pathlib import Path
from typing import Any

from django.conf import settings

from .providers import ProviderError, raise_for_bad_response, request_with_retries


class PromptAssistantError(RuntimeError):
    pass


def load_prompt_rules() -> str:
    path = Path(settings.PROMPT_RULES_PATH)
    if not path.is_absolute():
        path = Path(settings.BASE_DIR).parent / path
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise PromptAssistantError(f"无法读取预设提示词规则：{path}") from exc


def extract_assistant_result(data: Any) -> dict[str, Any]:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = ""

    if not isinstance(content, str):
        raise PromptAssistantError("DeepSeek 未返回有效内容")

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PromptAssistantError("DeepSeek 返回内容不是有效 JSON") from exc

    selling_points = parsed.get("selling_points")
    prompt = parsed.get("prompt")
    if not isinstance(selling_points, list) or not all(isinstance(item, str) for item in selling_points):
        raise PromptAssistantError("DeepSeek 返回的卖点格式无效")
    if not isinstance(prompt, str) or not prompt.strip():
        raise PromptAssistantError("DeepSeek 未返回最终视频提示词")
    if len(prompt) > 2500:
        raise PromptAssistantError("DeepSeek 返回的提示词超过2500个字符")

    return {
        "selling_points": [item.strip() for item in selling_points if item.strip()],
        "prompt": prompt.strip(),
    }


def mock_assistant_result(product_title: str) -> dict[str, Any]:
    name = product_title.strip() or "商品"
    return {
        "selling_points": ["保持商品原样", "突出核心质感", "适合短视频展示"],
        "prompt": (
            f"10s v 9:16, 4K. Bright clean ecommerce studio style. Ref 0.95. "
            f"Keep {name} identical. No logos. Use refs: finished static product only. "
            "0-3s: product centered on clean background. Camera slow push-in. No voice. Text: none. "
            "3-7s: close-up material details. Camera gentle orbit. Voice: \"Premium daily style.\" "
            "ONLY ONE floating gold text (top right, move right to left, 1.2s): \"New\". "
            "7-10s: final hero shot. Camera slow pull-back. Text (gold): \"Link en bio\" + cart. "
            "No extra objects. Keep colors/materials identical to ref. 4K."
        ),
    }


def deepseek_chat(user_text: str) -> dict[str, Any]:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return mock_assistant_result("")
    if not settings.DEEPSEEK_API_KEY:
        raise PromptAssistantError("缺少 DEEPSEEK_API_KEY")

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是跨境电商视频提示词专家。只输出 JSON，不要 Markdown。"
                    "JSON 格式必须是 {\"selling_points\":[\"...\"],\"prompt\":\"...\"}。"
                    "prompt 必须可直接用于视频生成，且不超过2500个字符。"
                ),
            },
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.4,
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = request_with_retries(
            "post",
            f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
            "DeepSeek prompt assistant",
            headers=headers,
            json=payload,
            timeout=90,
            ignore_system_proxy=True,
        )
        raise_for_bad_response(response, "DeepSeek prompt assistant")
    except ProviderError as exc:
        raise PromptAssistantError(str(exc)) from exc
    return extract_assistant_result(response.json())


def generate_video_prompt(product_title: str, product_detail: str) -> dict[str, Any]:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return mock_assistant_result(product_title)

    rules = load_prompt_rules()
    user_text = f"""
请根据商品信息先总结商品卖点，再严格依据预设提示词规则生成最终视频生成提示词。

商品标题：
{product_title}

商品详情：
{product_detail}

预设提示词规则：
{rules}

要求：
1. selling_points 输出 3-5 条，中文，短句。
2. prompt 使用英文为主，必要商品信息可保留专有名词。
3. prompt 必须遵守预设规则，尤其是 Keep product identical、Ref 0.95、禁止 AI 自行添加额外文字/配音/弹幕。
4. 只输出 JSON。
""".strip()
    return deepseek_chat(user_text)


def revise_video_prompt(
    product_title: str,
    product_detail: str,
    selling_points: list[str],
    current_prompt: str,
    revision_instruction: str,
) -> dict[str, Any]:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        result = mock_assistant_result(product_title)
        result["prompt"] = f"{current_prompt.strip()}\nRevision: {revision_instruction.strip()}"
        result["selling_points"] = selling_points or result["selling_points"]
        return result

    rules = load_prompt_rules()
    user_text = f"""
请根据用户修改要求，改写当前视频生成提示词。必须继续遵守预设提示词规则。

商品标题：
{product_title}

商品详情：
{product_detail}

已总结卖点：
{json.dumps(selling_points, ensure_ascii=False)}

当前提示词：
{current_prompt}

用户修改要求：
{revision_instruction}

预设提示词规则：
{rules}

要求：
1. selling_points 可沿用或小幅修正。
2. prompt 必须保留产品原样锁定、Ref 0.95、禁止额外内容等核心限制。
3. 只输出 JSON。
""".strip()
    return deepseek_chat(user_text)
