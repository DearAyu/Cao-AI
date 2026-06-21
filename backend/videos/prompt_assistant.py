import base64
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
        raise PromptAssistantError(f"鏃犳硶璇诲彇棰勮鎻愮ず璇嶈鍒欙細{path}") from exc


def extract_assistant_result(data: Any) -> dict[str, Any]:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = ""

    if not isinstance(content, str):
        raise PromptAssistantError("DeepSeek returned invalid content")

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
        raise PromptAssistantError("DeepSeek 杩斿洖鍐呭涓嶆槸鏈夋晥 JSON") from exc

    selling_points = parsed.get("selling_points")
    prompt = parsed.get("prompt")
    if not isinstance(selling_points, list) or not all(isinstance(item, str) for item in selling_points):
        raise PromptAssistantError("DeepSeek returned invalid selling_points")
    if not isinstance(prompt, str) or not prompt.strip():
        raise PromptAssistantError("DeepSeek 鏈繑鍥炴渶缁堣棰戞彁绀鸿瘝")
    if len(prompt) > 2500:
        raise PromptAssistantError("DeepSeek prompt exceeds 2500 characters")

    return {
        "selling_points": [item.strip() for item in selling_points if item.strip()],
        "prompt": prompt.strip(),
    }


def mock_assistant_result(product_title: str) -> dict[str, Any]:
    name = product_title.strip() or "鍟嗗搧"
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


def image_data_url(image) -> str:
    content_type = getattr(image, "content_type", "") or "image/png"
    image.open("rb") if hasattr(image, "open") else None
    try:
        raw = image.read()
    finally:
        image.close() if hasattr(image, "close") else None
    return f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"


def build_user_content(user_text: str, reference_image=None):
    if not reference_image:
        return user_text
    return [
        {"type": "text", "text": f"{user_text}\n\nReference image: identify product appearance, color, shape, material, and visible selling points."},
        {"type": "image_url", "image_url": {"url": image_data_url(reference_image)}},
    ]


def deepseek_chat(user_text: str, reference_image=None) -> dict[str, Any]:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return mock_assistant_result("")
    if not settings.DEEPSEEK_API_KEY:
        raise PromptAssistantError("缂哄皯 DEEPSEEK_API_KEY")

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a cross-border ecommerce video prompt expert. "
                    "Return JSON only, no Markdown. "
                    "The JSON format must be {\"selling_points\":[\"...\"],\"prompt\":\"...\"}. "
                    "The prompt must be ready for video generation and no longer than 2500 characters."
                ),
            },
            {"role": "user", "content": build_user_content(user_text, reference_image)},
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


def generate_video_prompt(video_brief: str, product_title: str, product_detail: str, reference_image=None) -> dict[str, Any]:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return mock_assistant_result(product_title)

    rules = load_prompt_rules()
    user_text = f"""
璇锋牴鎹晢鍝佷俊鎭厛鎬荤粨鍟嗗搧鍗栫偣锛屽啀涓ユ牸渚濇嵁棰勮鎻愮ず璇嶈鍒欑敓鎴愭渶缁堣棰戠敓鎴愭彁绀鸿瘝銆?
User video brief: {video_brief or "未填写"}

鍟嗗搧鏍囬锛?{product_title}

鍟嗗搧璇︽儏锛?{product_detail}

棰勮鎻愮ず璇嶈鍒欙細
{rules}

瑕佹眰锛?1. selling_points 杈撳嚭 3-5 鏉★紝涓枃锛岀煭鍙ャ€?2. prompt 浣跨敤鑻辨枃涓轰富锛屽繀瑕佸晢鍝佷俊鎭彲淇濈暀涓撴湁鍚嶈瘝銆?3. prompt 蹇呴』閬靛畧棰勮瑙勫垯锛屽挨鍏舵槸 Keep product identical銆丷ef 0.95銆佺姝?AI 鑷娣诲姞棰濆鏂囧瓧/閰嶉煶/寮瑰箷銆?4. 鍙緭鍑?JSON銆?""".strip()
    return deepseek_chat(user_text, reference_image=reference_image)


def revise_video_prompt(
    video_brief: str,
    product_title: str,
    product_detail: str,
    selling_points: list[str],
    current_prompt: str,
    revision_instruction: str,
    reference_image=None,
) -> dict[str, Any]:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        result = mock_assistant_result(product_title)
        result["prompt"] = f"{current_prompt.strip()}\nRevision: {revision_instruction.strip()}"
        result["selling_points"] = selling_points or result["selling_points"]
        return result

    rules = load_prompt_rules()
    user_text = f"""
璇锋牴鎹敤鎴蜂慨鏀硅姹傦紝鏀瑰啓褰撳墠瑙嗛鐢熸垚鎻愮ず璇嶃€傚繀椤荤户缁伒瀹堥璁炬彁绀鸿瘝瑙勫垯銆?
User video brief: {video_brief or "未填写"}

鍟嗗搧鏍囬锛?{product_title}

鍟嗗搧璇︽儏锛?{product_detail}

宸叉€荤粨鍗栫偣锛?{json.dumps(selling_points, ensure_ascii=False)}

褰撳墠鎻愮ず璇嶏細
{current_prompt}

鐢ㄦ埛淇敼瑕佹眰锛?{revision_instruction}

棰勮鎻愮ず璇嶈鍒欙細
{rules}

瑕佹眰锛?1. selling_points 鍙部鐢ㄦ垨灏忓箙淇銆?2. prompt 蹇呴』淇濈暀浜у搧鍘熸牱閿佸畾銆丷ef 0.95銆佺姝㈤澶栧唴瀹圭瓑鏍稿績闄愬埗銆?3. 鍙緭鍑?JSON銆?""".strip()
    return deepseek_chat(user_text, reference_image=reference_image)
