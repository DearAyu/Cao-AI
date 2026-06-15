import time
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

from .models import ImageJob
from .providers import ProviderError, image_as_data_url, raise_for_bad_response, request_with_retries


@dataclass
class BaseImageProvider:
    name: str

    def submit(self, job: ImageJob) -> dict[str, Any]:
        raise NotImplementedError

    def refresh(self, job: ImageJob) -> dict[str, Any]:
        raise NotImplementedError


class MockImageProvider(BaseImageProvider):
    def __init__(self, name="mock"):
        super().__init__(name=name)

    def submit(self, job: ImageJob) -> dict[str, Any]:
        return {
            "status": ImageJob.Status.SUBMITTED,
            "remote_task_id": f"mock-image-{job.provider}-{int(time.time() * 1000)}",
            "raw_response": {"mock": "submitted"},
        }

    def refresh(self, job: ImageJob) -> dict[str, Any]:
        if job.status == ImageJob.Status.SUBMITTED:
            return {"status": ImageJob.Status.PROCESSING, "raw_response": {"mock": "processing"}}
        return {"status": job.status, "raw_response": {"mock": "unchanged"}}


class AliWanImageProvider(BaseImageProvider):
    def __init__(self):
        super().__init__(name="aliyun")

    @property
    def headers(self):
        if not settings.ALIYUN_API_KEY:
            raise ProviderError("缺少 ALIYUN_API_KEY")
        return {
            "Authorization": f"Bearer {settings.ALIYUN_API_KEY}",
            "Content-Type": "application/json",
        }

    def submit(self, job: ImageJob) -> dict[str, Any]:
        payload = {
            "model": settings.ALIYUN_IMAGE_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_as_data_url(job)},
                            {"text": job.prompt or "基于参考图生成一张高质感跨境电商商品图。"},
                        ],
                    }
                ]
            },
            "parameters": {
                "size": job.size,
                "n": job.count,
                "watermark": False,
            },
        }
        job.raw_request = payload
        response = request_with_retries(
            "post",
            f"{settings.ALIYUN_BASE_URL.rstrip('/')}/services/aigc/multimodal-generation/generation",
            "Aliyun image",
            json=payload,
            headers=self.headers,
            timeout=60,
        )
        raise_for_bad_response(response, "Aliyun image")
        data = response.json()
        result_urls = extract_image_urls(data)
        if result_urls:
            return {
                "status": ImageJob.Status.SUCCEEDED,
                "remote_task_id": str(data.get("request_id") or f"aliyun-image-{int(time.time() * 1000)}"),
                "result_urls": result_urls,
                "raw_response": data,
            }
        task_id = data.get("output", {}).get("task_id") or data.get("task_id")
        if not task_id:
            raise ProviderError("阿里生图返回中缺少任务 ID 或结果图片 URL")
        return {
            "status": ImageJob.Status.SUBMITTED,
            "remote_task_id": str(task_id),
            "raw_response": data,
        }

    def refresh(self, job: ImageJob) -> dict[str, Any]:
        response = request_with_retries(
            "get",
            f"{settings.ALIYUN_BASE_URL.rstrip('/')}/tasks/{job.remote_task_id}",
            "Aliyun image",
            headers=self.headers,
            timeout=30,
        )
        raise_for_bad_response(response, "Aliyun image")
        data = response.json()
        return normalize_image_result(data)


class SeedreamImageProvider(BaseImageProvider):
    def __init__(self):
        super().__init__(name="seedream")

    @property
    def headers(self):
        if not settings.VOLCENGINE_API_KEY:
            raise ProviderError("缺少 VOLCENGINE_API_KEY")
        return {"Authorization": f"Bearer {settings.VOLCENGINE_API_KEY}", "Content-Type": "application/json"}

    def submit(self, job: ImageJob) -> dict[str, Any]:
        payload = {
            "model": settings.SEEDREAM_IMAGE_MODEL,
            "prompt": job.prompt or "基于参考图生成一张高质感跨境电商商品图。",
            "image": image_as_data_url(job),
            "size": job.size,
            "response_format": "url",
            "watermark": False,
        }
        job.raw_request = payload
        response = request_with_retries(
            "post",
            f"{settings.VOLCENGINE_BASE_URL.rstrip('/')}/images/generations",
            "Seedream image",
            json=payload,
            headers=self.headers,
            timeout=60,
        )
        raise_for_bad_response(response, "Seedream image")
        data = response.json()
        result_urls = extract_image_urls(data)
        if not result_urls:
            raise ProviderError("字节生图返回中缺少结果图片 URL")
        return {
            "status": ImageJob.Status.SUCCEEDED,
            "remote_task_id": str(data.get("id") or f"seedream-{int(time.time() * 1000)}"),
            "result_urls": result_urls,
            "raw_response": data,
        }

    def refresh(self, job: ImageJob) -> dict[str, Any]:
        return {"status": job.status, "raw_response": job.raw_response}


def normalize_image_result(raw: dict[str, Any]) -> dict[str, Any]:
    output = raw.get("output", {})
    status_text = str(output.get("task_status") or raw.get("task_status") or "").lower()
    if status_text in {"succeeded", "success", "completed", "finished"}:
        return {
            "status": ImageJob.Status.SUCCEEDED,
            "result_urls": extract_image_urls(raw),
            "raw_response": raw,
        }
    if status_text in {"failed", "error", "canceled", "cancelled"}:
        code = output.get("code") or raw.get("code")
        message = output.get("message") or raw.get("message") or raw.get("error") or "生成失败"
        return {
            "status": ImageJob.Status.FAILED,
            "error_message": f"{code}: {message}" if code and message else message,
            "raw_response": raw,
        }
    return {"status": ImageJob.Status.PROCESSING, "raw_response": raw}


def extract_image_urls(raw: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in raw.get("data", []) or []:
        url = item.get("url") or item.get("image_url")
        if url:
            urls.append(url)

    output = raw.get("output", {})
    for result in output.get("results", []) or []:
        url = result.get("url") or result.get("image_url")
        if url:
            urls.append(url)
    for choice in output.get("choices", []) or []:
        message = choice.get("message", {})
        for content in message.get("content", []) or []:
            if isinstance(content, dict):
                url = content.get("image") or content.get("url") or content.get("image_url")
                if isinstance(url, str):
                    urls.append(url)
                elif isinstance(url, dict) and url.get("url"):
                    urls.append(url["url"])
    return urls


def get_image_provider(name: str) -> BaseImageProvider:
    if settings.VIDEO_PROVIDER_FORCE_MOCK:
        return MockImageProvider(name=name)
    if name == ImageJob.Provider.ALIYUN:
        return AliWanImageProvider()
    if name == ImageJob.Provider.SEEDREAM:
        return SeedreamImageProvider()
    raise ProviderError(f"不支持的 image provider: {name}")
