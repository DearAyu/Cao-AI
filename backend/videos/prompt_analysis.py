import base64
import mimetypes
from typing import Any

from django.conf import settings

from .providers import ProviderError, raise_for_bad_response, request_with_retries


PROMPT_ANALYSIS_INSTRUCTION = (
    "只输出一个中文视频生成提示词，不要解释或添加其他内容。提示词需描述商品、卖点、"
    "影棚灯光、镜头运动、节奏和构图，且不超过2500个字符。"
)
MOCK_ANALYSIS_PROMPT = (
    "商品置于整洁的专业影棚中央，突出材质细节与核心卖点；柔和主光配合轮廓光塑造高级质感，"
    "镜头从中景平滑推进至特写并轻微环绕，节奏舒缓利落，主体居中构图并保留适度留白。"
)


class PromptAnalysisError(RuntimeError):
    pass


def image_data_url(uploaded_file) -> str:
    content_type = getattr(uploaded_file, "content_type", None)
    if not content_type:
        content_type = mimetypes.guess_type(getattr(uploaded_file, "name", ""))[0] or "image/png"
    try:
        raw = uploaded_file.read()
    finally:
        uploaded_file.seek(0)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def extract_prompt(data: Any) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None

    if isinstance(content, str):
        prompt = content.strip()
    elif isinstance(content, list):
        prompt = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ).strip()
    else:
        prompt = ""

    if not prompt:
        raise PromptAnalysisError("豆包未返回视频提示词")
    if len(prompt) > 2500:
        raise PromptAnalysisError("豆包返回的视频提示词超过2500个字符")
    return prompt


def analyze_product_image(uploaded_file) -> str:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return MOCK_ANALYSIS_PROMPT
    if not settings.VOLCENGINE_API_KEY:
        raise PromptAnalysisError("缺少 VOLCENGINE_API_KEY")

    payload = {
        "model": settings.DOUBAO_SEED_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_url(uploaded_file)}},
                    {"type": "text", "text": PROMPT_ANALYSIS_INSTRUCTION},
                ],
            }
        ],
        "max_tokens": 1000,
    }
    headers = {
        "Authorization": f"Bearer {settings.VOLCENGINE_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = request_with_retries(
            "post",
            f"{settings.VOLCENGINE_BASE_URL.rstrip('/')}/chat/completions",
            "Doubao prompt analysis",
            headers=headers,
            json=payload,
            timeout=60,
        )
        raise_for_bad_response(response, "Doubao prompt analysis")
    except ProviderError as exc:
        raise PromptAnalysisError(str(exc)) from exc
    return extract_prompt(response.json())
