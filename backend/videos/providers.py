import base64
from io import BytesIO
import mimetypes
import time
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings
from requests import exceptions as request_exceptions

from .models import VideoJob


class ProviderError(RuntimeError):
    pass


def request_with_retries(method: str, url: str, provider_name: str, **kwargs) -> requests.Response:
    retryable_errors = (
        request_exceptions.ConnectionError,
        request_exceptions.SSLError,
        request_exceptions.Timeout,
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            return getattr(requests, method)(url, **kwargs)
        except retryable_errors as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(0.6 * attempt)
    raise ProviderError(f"{provider_name} network error after retries: {last_error}") from last_error


def raise_for_bad_response(response: requests.Response, provider_name: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = getattr(response, "text", "") or ""
        status_code = getattr(response, "status_code", "unknown")
        raise ProviderError(f"{provider_name} HTTP {status_code}: {body[:1000]}") from exc


def image_as_data_url(job: VideoJob) -> str:
    content_type = mimetypes.guess_type(job.source_image.name)[0] or "image/png"
    job.source_image.open("rb")
    try:
        raw = job.source_image.read()
    finally:
        job.source_image.close()
    raw, content_type = shrink_image_if_possible(raw, content_type)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def shrink_image_if_possible(raw: bytes, content_type: str) -> tuple[bytes, str]:
    max_bytes = int(getattr(settings, "PROVIDER_IMAGE_MAX_BYTES", 2_000_000))
    if len(raw) <= max_bytes:
        return raw, content_type
    try:
        from PIL import Image
    except ImportError:
        return raw, content_type

    try:
        image = Image.open(BytesIO(raw))
        image.thumbnail((1600, 1600))
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        compressed = output.getvalue()
        return (compressed, "image/jpeg") if len(compressed) < len(raw) else (raw, content_type)
    except Exception:
        return raw, content_type


def aliyun_duration(duration: int) -> int:
    return duration if duration in {3, 4, 5} else 5


def is_wan27_model(model_name: str | None = None) -> bool:
    return str(model_name or settings.ALIYUN_MODEL).startswith("wan2.7")


def build_aliyun_payload(job: VideoJob) -> dict[str, Any]:
    image_url = image_as_data_url(job)
    model_name = job.model_name or settings.ALIYUN_MODEL
    resolution = (job.resolution or "720p").upper()
    payload: dict[str, Any] = {
        "model": model_name,
        "input": {"prompt": job.prompt or "Create a polished ecommerce product video."},
    }
    if is_wan27_model(model_name):
        payload["input"]["media"] = [{"type": "first_frame", "url": image_url}]
        payload["parameters"] = {"duration": job.duration, "resolution": resolution}
    else:
        payload["input"]["img_url"] = image_url
        payload["parameters"] = {"duration": aliyun_duration(job.duration), "resolution": resolution}
    return payload


@dataclass
class BaseVideoProvider:
    name: str

    def submit(self, job: VideoJob) -> str:
        raise NotImplementedError

    def refresh(self, job: VideoJob) -> dict[str, Any]:
        raise NotImplementedError


class MockVideoProvider(BaseVideoProvider):
    def __init__(self, name="mock"):
        super().__init__(name=name)

    def submit(self, job: VideoJob) -> str:
        return f"mock-{job.provider}-{int(time.time() * 1000)}"

    def refresh(self, job: VideoJob) -> dict[str, Any]:
        if job.status == VideoJob.Status.SUBMITTED:
            return {"status": VideoJob.Status.PROCESSING, "raw_response": {"mock": "processing"}}
        return {"status": job.status, "raw_response": {"mock": "unchanged"}}


class VolcengineSeedanceProvider(BaseVideoProvider):
    def __init__(self):
        super().__init__(name="volcengine")

    @property
    def headers(self):
        if not settings.VOLCENGINE_API_KEY:
            raise ProviderError("缂哄皯 VOLCENGINE_API_KEY")
        return {"Authorization": f"Bearer {settings.VOLCENGINE_API_KEY}", "Content-Type": "application/json"}

    def submit(self, job: VideoJob) -> str:
        payload = {
            "model": job.model_name or settings.VOLCENGINE_MODEL,
            "content": [
                {"type": "text", "text": job.prompt or "Create a polished ecommerce product video."},
                {"type": "image_url", "image_url": {"url": image_as_data_url(job)}},
            ],
            "duration": job.duration,
            "ratio": job.aspect_ratio,
            "resolution": job.resolution or "720p",
        }
        job.raw_request = payload
        response = request_with_retries(
            "post",
            f"{settings.VOLCENGINE_BASE_URL.rstrip('/')}/contents/generations/tasks",
            "Volcengine",
            json=payload,
            headers=self.headers,
            timeout=60,
        )
        raise_for_bad_response(response, "Volcengine")
        data = response.json()
        job.raw_response = data
        task_id = data.get("id") or data.get("task_id") or data.get("data", {}).get("id")
        if not task_id:
            raise ProviderError("鐏北杩斿洖涓己灏戜换鍔?ID")
        return str(task_id)

    def refresh(self, job: VideoJob) -> dict[str, Any]:
        response = request_with_retries(
            "get",
            f"{settings.VOLCENGINE_BASE_URL.rstrip('/')}/contents/generations/tasks/{job.remote_task_id}",
            "Volcengine",
            headers=self.headers,
            timeout=30,
        )
        raise_for_bad_response(response, "Volcengine")
        data = response.json()
        status_text = str(data.get("status") or data.get("data", {}).get("status") or "").lower()
        video_url = data.get("content", {}).get("video_url") or data.get("data", {}).get("video_url")
        return normalize_provider_result(status_text, video_url, data)


class AliWanxiangProvider(BaseVideoProvider):
    def __init__(self):
        super().__init__(name="aliyun")

    @property
    def headers(self):
        if not settings.ALIYUN_API_KEY:
            raise ProviderError("缂哄皯 ALIYUN_API_KEY")
        return {
            "Authorization": f"Bearer {settings.ALIYUN_API_KEY}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }

    def submit(self, job: VideoJob) -> str:
        payload = build_aliyun_payload(job)
        job.raw_request = payload
        response = request_with_retries(
            "post",
            f"{settings.ALIYUN_BASE_URL.rstrip('/')}/services/aigc/video-generation/video-synthesis",
            "Aliyun",
            json=payload,
            headers=self.headers,
            timeout=60,
        )
        raise_for_bad_response(response, "Aliyun")
        data = response.json()
        job.raw_response = data
        task_id = data.get("output", {}).get("task_id") or data.get("task_id")
        if not task_id:
            raise ProviderError("闃块噷杩斿洖涓己灏戜换鍔?ID")
        return str(task_id)

    def refresh(self, job: VideoJob) -> dict[str, Any]:
        response = request_with_retries(
            "get",
            f"{settings.ALIYUN_BASE_URL.rstrip('/')}/tasks/{job.remote_task_id}",
            "Aliyun",
            headers=self.headers,
            timeout=30,
        )
        raise_for_bad_response(response, "Aliyun")
        data = response.json()
        output = data.get("output", {})
        status_text = str(output.get("task_status") or data.get("task_status") or "").lower()
        video_url = output.get("video_url") or output.get("url")
        return self.refresh_result_from_data(data, status_text, video_url)

    def refresh_result_from_data(
        self,
        data: dict[str, Any],
        status_text: str | None = None,
        video_url: str | None = None,
    ) -> dict[str, Any]:
        output = data.get("output", {})
        normalized_status = str(status_text or output.get("task_status") or data.get("task_status") or "").lower()
        normalized_video_url = video_url or output.get("video_url") or output.get("url")
        return normalize_provider_result(normalized_status, normalized_video_url, data)


def normalize_provider_result(status_text: str, result_url: str | None, raw: dict[str, Any]) -> dict[str, Any]:
    if status_text in {"succeeded", "success", "completed", "finished"}:
        return {"status": VideoJob.Status.SUCCEEDED, "result_url": result_url, "raw_response": raw}
    if status_text in {"failed", "error", "canceled", "cancelled"}:
        output = raw.get("output", {})
        code = output.get("code") or raw.get("code")
        message = output.get("message") or raw.get("message") or raw.get("error") or "生成失败"
        error_message = f"{code}: {message}" if code and message else message
        return {
            "status": VideoJob.Status.FAILED,
            "error_message": error_message,
            "raw_response": raw,
        }
    return {"status": VideoJob.Status.PROCESSING, "raw_response": raw}


def get_provider(name: str) -> BaseVideoProvider:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return MockVideoProvider(name=name)
    if name == VideoJob.Provider.VOLCENGINE:
        return VolcengineSeedanceProvider()
    if name == VideoJob.Provider.ALIYUN:
        return AliWanxiangProvider()
    raise ProviderError(f"涓嶆敮鎸佺殑 provider: {name}")
