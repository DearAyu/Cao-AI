import base64
from pathlib import Path
from shutil import copyfile
from urllib.parse import urlparse

import requests
from django.conf import settings

from .models import ImageJob, VideoJob
from . import providers
from . import image_providers


def submit_job(job: VideoJob) -> VideoJob:
    provider = providers.get_provider(job.provider)
    job.status = VideoJob.Status.PENDING
    try:
        job.remote_task_id = provider.submit(job)
        job.status = VideoJob.Status.SUBMITTED
        job.error_message = ""
    except Exception as exc:
        job.status = VideoJob.Status.FAILED
        job.error_message = str(exc)
    job.save()
    return job


def refresh_job(job: VideoJob) -> VideoJob:
    if job.status in {VideoJob.Status.SUCCEEDED, VideoJob.Status.FAILED}:
        return job
    if not job.remote_task_id:
        return job

    provider = get_refresh_provider(job)
    try:
        result = provider.refresh(job)
        job.status = result.get("status", job.status)
        job.raw_response = result.get("raw_response", job.raw_response)
        job.error_message = result.get("error_message", "")
        result_url = result.get("result_url")
        if job.status == VideoJob.Status.SUCCEEDED and not job.result_video:
            if result_url:
                path = download_file(result_url, job)
            elif result.get("mock_result"):
                path = write_mock_video_file(job)
            else:
                path = None
            if path:
                job.result_video.name = str(path.relative_to(settings.MEDIA_ROOT)).replace("\\", "/")
    except Exception as exc:
        job.status = VideoJob.Status.FAILED
        job.error_message = str(exc)
    job.save()
    return job


def get_refresh_provider(job: VideoJob):
    if job.remote_task_id.startswith("mock-"):
        return providers.MockVideoProvider(name=job.provider)
    return providers.get_provider(job.provider)


def download_file(url: str, job: VideoJob) -> Path:
    results_dir = Path(settings.MEDIA_ROOT) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(urlparse(url).path).suffix or ".mp4"
    target = results_dir / f"job-{job.pk}{suffix}"
    response = requests.get(url, stream=True, timeout=settings.VIDEO_DOWNLOAD_TIMEOUT)
    response.raise_for_status()
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 128):
            if chunk:
                handle.write(chunk)
    return target


def write_mock_video_file(job: VideoJob) -> Path:
    results_dir = Path(settings.MEDIA_ROOT) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    target = results_dir / f"job-{job.pk}-mock.mp4"
    if target.exists() and target.stat().st_size:
        return target

    sample = next(
        (
            path
            for path in sorted(results_dir.glob("*.mp4"), key=lambda item: item.stat().st_size)
            if path.resolve() != target.resolve() and path.stat().st_size > 1024
        ),
        None,
    )
    if sample:
        copyfile(sample, target)
    else:
        target.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08free")
    return target


def submit_image_job(job: ImageJob) -> ImageJob:
    provider = image_providers.get_image_provider(job.provider)
    job.status = ImageJob.Status.PENDING
    try:
        result = provider.submit(job)
        apply_image_result(job, result)
        job.error_message = ""
    except Exception as exc:
        job.status = ImageJob.Status.FAILED
        job.error_message = str(exc)
    job.save()
    return job


def refresh_image_job(job: ImageJob) -> ImageJob:
    if job.status in {ImageJob.Status.SUCCEEDED, ImageJob.Status.FAILED}:
        return job
    if not job.remote_task_id:
        return job

    provider = get_image_refresh_provider(job)
    try:
        result = provider.refresh(job)
        apply_image_result(job, result)
    except Exception as exc:
        job.status = ImageJob.Status.FAILED
        job.error_message = str(exc)
    job.save()
    return job


def apply_image_result(job: ImageJob, result: dict) -> None:
    job.status = result.get("status", job.status)
    job.remote_task_id = result.get("remote_task_id", job.remote_task_id)
    job.raw_response = result.get("raw_response", job.raw_response)
    job.error_message = result.get("error_message", "")
    result_urls = result.get("result_urls") or []
    if job.status == ImageJob.Status.SUCCEEDED and result_urls and not job.result_images:
        job.result_images = [
            str(download_image(url, job, index).relative_to(settings.MEDIA_ROOT)).replace("\\", "/")
            for index, url in enumerate(result_urls, start=1)
        ]
    result_images_base64 = result.get("result_images_base64") or []
    if job.status == ImageJob.Status.SUCCEEDED and result_images_base64 and not job.result_images:
        job.result_images = [
            str(write_base64_image(image, job, index).relative_to(settings.MEDIA_ROOT)).replace("\\", "/")
            for index, image in enumerate(result_images_base64, start=1)
        ]


def get_image_refresh_provider(job: ImageJob):
    if job.remote_task_id.startswith("mock-image-"):
        return image_providers.MockImageProvider(name=job.provider)
    return image_providers.get_image_provider(job.provider)


def download_image(url: str, job: ImageJob, index: int) -> Path:
    images_dir = Path(settings.MEDIA_ROOT) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(urlparse(url).path).suffix or ".png"
    target = images_dir / f"job-{job.pk}-{index}{suffix}"
    response = requests.get(url, stream=True, timeout=settings.VIDEO_DOWNLOAD_TIMEOUT)
    response.raise_for_status()
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 128):
            if chunk:
                handle.write(chunk)
    return target


def write_base64_image(image_base64: str, job: ImageJob, index: int) -> Path:
    images_dir = Path(settings.MEDIA_ROOT) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / f"job-{job.pk}-{index}.png"
    _, _, payload = image_base64.partition(",")
    raw = base64.b64decode(payload or image_base64)
    target.write_bytes(raw)
    return target
