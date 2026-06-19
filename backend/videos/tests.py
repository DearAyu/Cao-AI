import base64
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .image_providers import AliWanImageProvider, SeedreamImageProvider
from .models import ImageJob, VideoJob
from .prompt_analysis import (
    PROMPT_ANALYSIS_INSTRUCTION,
    PromptAnalysisError,
    analyze_product_image,
    extract_prompt,
    image_data_url,
)
from .providers import AliWanxiangProvider, VolcengineSeedanceProvider


MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT, VIDEO_PROVIDER_FORCE_MOCK=True)
class VideoJobApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def image_file(self, name="product.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            content_type="image/png",
        )

    def test_create_requires_source_image(self):
        response = self.client.post(
            reverse("video-job-list"),
            {"provider": "volcengine", "prompt": "Show the product in a bright studio"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source_image", response.data)

    def test_create_rejects_unknown_provider(self):
        response = self.client.post(
            reverse("video-job-list"),
            {
                "provider": "unknown",
                "prompt": "Create a smooth product reveal",
                "source_image": self.image_file(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("provider", response.data)

    def test_create_submits_mock_job_and_lists_it(self):
        response = self.client.post(
            reverse("video-job-list"),
            {
                "provider": "volcengine",
                "prompt": "A premium marketplace product video",
                "source_image": self.image_file(),
                "aspect_ratio": "1:1",
                "duration": 5,
                "resolution": "1080p",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "submitted")
        self.assertEqual(response.data["resolution"], "1080p")
        self.assertTrue(response.data["remote_task_id"].startswith("mock-"))

        list_response = self.client.get(reverse("video-job-list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data["results"]), 1)

    def test_detail_refresh_downloads_completed_result(self):
        create_response = self.client.post(
            reverse("video-job-list"),
            {
                "provider": "aliyun",
                "prompt": "Rotate the product on a soft gradient set",
                "source_image": self.image_file(),
            },
            format="multipart",
        )
        job_id = create_response.data["id"]
        VideoJob.objects.filter(id=job_id).update(remote_task_id="real-task-123", status="submitted")

        class FinishedProvider:
            def submit(self, job):
                return "unused"

            def refresh(self, job):
                return {
                    "status": "succeeded",
                    "result_url": "https://example.test/video.mp4",
                    "raw_response": {"ok": True},
                }

        with patch("videos.providers.get_provider", return_value=FinishedProvider()):
            with patch("videos.services.download_file", return_value=Path(MEDIA_ROOT) / "results" / "demo.mp4") as download:
                response = self.client.get(reverse("video-job-detail", args=[job_id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "succeeded")
        self.assertIn("results/demo.mp4", response.data["result_video"])
        download.assert_called_once()

    @override_settings(VIDEO_PROVIDER_FORCE_MOCK=False)
    def test_mock_history_keeps_using_mock_refresh_when_real_mode_is_enabled(self):
        job = VideoJob.objects.create(
            provider="volcengine",
            status="submitted",
            prompt="Mock history",
            source_image=self.image_file(),
            remote_task_id="mock-volcengine-history",
        )

        response = self.client.get(reverse("video-job-detail", args=[job.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "processing")
        self.assertEqual(response.data["raw_response"], {"mock": "processing"})


@override_settings(
    ALIYUN_API_KEY="test-key",
    ALIYUN_MODEL="wanx2.1-i2v-turbo",
    ALIYUN_BASE_URL="https://dashscope.aliyuncs.com/api/v1",
)
class AliWanxiangProviderTests(TestCase):
    def test_submit_sends_base64_image_and_supported_parameters(self):
        job = VideoJob.objects.create(
            provider="aliyun",
            prompt="展示商品质感",
            aspect_ratio="9:16",
            duration=10,
            resolution="480p",
            source_image=SimpleUploadedFile(
                "product.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                content_type="image/png",
            ),
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"output": {"task_id": "task-1", "task_status": "PENDING"}}

        with patch("videos.providers.requests.post", return_value=Response()) as post:
            task_id = AliWanxiangProvider().submit(job)

        payload = post.call_args.kwargs["json"]
        self.assertEqual(task_id, "task-1")
        self.assertTrue(payload["input"]["img_url"].startswith("data:image/png;base64,"))
        self.assertNotIn("ratio", payload["parameters"])
        self.assertEqual(payload["parameters"]["resolution"], "480P")
        self.assertEqual(payload["parameters"]["duration"], 5)

    @override_settings(ALIYUN_MODEL="wan2.7-i2v")
    def test_submit_uses_wan27_media_protocol(self):
        job = VideoJob.objects.create(
            provider="aliyun",
            prompt="展示商品质感",
            aspect_ratio="9:16",
            duration=10,
            resolution="480p",
            source_image=SimpleUploadedFile(
                "product.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                content_type="image/png",
            ),
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"output": {"task_id": "task-wan27", "task_status": "PENDING"}}

        with patch("videos.providers.requests.post", return_value=Response()) as post:
            task_id = AliWanxiangProvider().submit(job)

        payload = post.call_args.kwargs["json"]
        self.assertEqual(task_id, "task-wan27")
        self.assertNotIn("img_url", payload["input"])
        self.assertEqual(payload["input"]["media"][0]["type"], "first_frame")
        self.assertTrue(payload["input"]["media"][0]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(payload["parameters"]["duration"], 10)

    def test_submit_uses_job_model_name_for_aliyun_payload(self):
        job = VideoJob.objects.create(
            provider="aliyun",
            model_name="wan2.7-i2v",
            prompt="展示商品质感",
            aspect_ratio="9:16",
            duration=10,
            resolution="480p",
            source_image=SimpleUploadedFile(
                "product.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                content_type="image/png",
            ),
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"output": {"task_id": "task-job-model", "task_status": "PENDING"}}

        with patch("videos.providers.requests.post", return_value=Response()) as post:
            task_id = AliWanxiangProvider().submit(job)

        payload = post.call_args.kwargs["json"]
        self.assertEqual(task_id, "task-job-model")
        self.assertEqual(payload["model"], "wan2.7-i2v")
        self.assertIn("media", payload["input"])
        self.assertEqual(payload["parameters"]["resolution"], "480P")

    def test_failed_refresh_uses_nested_aliyun_error_message(self):
        result = AliWanxiangProvider().refresh_result_from_data(
            {
                "output": {
                    "task_status": "FAILED",
                    "code": "InvalidParameter",
                    "message": "Field required: input.media",
                }
            }
        )

        self.assertEqual(result["status"], VideoJob.Status.FAILED)
        self.assertEqual(result["error_message"], "InvalidParameter: Field required: input.media")


@override_settings(
    VOLCENGINE_API_KEY="test-key",
    VOLCENGINE_MODEL="seedance-1-0-lite-i2v-250428",
    VOLCENGINE_BASE_URL="https://ark.cn-beijing.volces.com/api/v3",
)
class VolcengineSeedanceProviderTests(TestCase):
    def test_submit_sends_base64_image_content(self):
        job = VideoJob.objects.create(
            provider="volcengine",
            model_name="doubao-seedance-2-0-fast-260128",
            prompt="Create a premium product reveal",
            aspect_ratio="9:16",
            duration=5,
            resolution="1080p",
            source_image=SimpleUploadedFile(
                "product.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                content_type="image/png",
            ),
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"id": "seedance-task-1"}

        with patch("videos.providers.requests.post", return_value=Response()) as post:
            task_id = VolcengineSeedanceProvider().submit(job)

        payload = post.call_args.kwargs["json"]
        self.assertEqual(task_id, "seedance-task-1")
        self.assertEqual(payload["model"], "doubao-seedance-2-0-fast-260128")
        self.assertEqual(payload["content"][1]["image_url"].keys(), {"url"})
        self.assertTrue(payload["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(payload["resolution"], "1080p")


@override_settings(
    VIDEO_PROVIDER_FORCE_MOCK=False,
    VOLCENGINE_API_KEY="test-key",
    VOLCENGINE_BASE_URL="https://ark.example/api/v3",
    DOUBAO_SEED_MODEL="doubao-seed-test-model",
)
class PromptAnalysisProviderTests(TestCase):
    ONE_PIXEL_PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def image_file(self):
        return SimpleUploadedFile("product.png", self.ONE_PIXEL_PNG, content_type="image/png")

    def test_analyze_uses_configured_model_and_multimodal_content(self):
        class Response:
            def json(self):
                return {"choices": [{"message": {"content": "高质感商品展示视频"}}]}

        with patch("videos.prompt_analysis.request_with_retries", return_value=Response()) as request:
            with patch("videos.prompt_analysis.raise_for_bad_response"):
                result = analyze_product_image(self.image_file())

        self.assertEqual(result, "高质感商品展示视频")
        self.assertEqual(request.call_args.args[:3], ("post", "https://ark.example/api/v3/chat/completions", "Doubao prompt analysis"))
        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "doubao-seed-test-model")
        self.assertEqual(payload["max_tokens"], 1000)
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "image_url", "image_url": {"url": image_data_url(self.image_file())}})
        self.assertEqual(content[1], {"type": "text", "text": PROMPT_ANALYSIS_INSTRUCTION})

    def test_image_data_url_reads_valid_png_and_rewinds_file(self):
        uploaded_file = self.image_file()

        result = image_data_url(uploaded_file)

        prefix, encoded = result.split(",", 1)
        self.assertEqual(prefix, "data:image/png;base64")
        self.assertEqual(base64.b64decode(encoded), self.ONE_PIXEL_PNG)
        self.assertEqual(uploaded_file.tell(), 0)

    def test_instruction_requests_a_single_chinese_video_prompt(self):
        for requirement in ("一个", "中文", "商品", "卖点", "影棚灯光", "镜头运动", "节奏", "构图", "2500"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, PROMPT_ANALYSIS_INSTRUCTION)

    def test_extract_prompt_supports_string_and_list_text_content(self):
        string_data = {"choices": [{"message": {"content": "商品缓慢旋转展示"}}]}
        list_data = {
            "choices": [{"message": {"content": [{"type": "text", "text": "镜头平滑推进"}]}}]
        }

        self.assertEqual(extract_prompt(string_data), "商品缓慢旋转展示")
        self.assertEqual(extract_prompt(list_data), "镜头平滑推进")

    def test_extract_prompt_rejects_missing_output(self):
        with self.assertRaises(PromptAnalysisError):
            extract_prompt({"choices": [{"message": {"content": []}}]})

    def test_extract_prompt_rejects_output_over_2500_characters(self):
        data = {"choices": [{"message": {"content": "商" * 2501}}]}

        with self.assertRaises(PromptAnalysisError):
            extract_prompt(data)


class PromptAnalysisApiTests(TestCase):
    ONE_PIXEL_PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def setUp(self):
        self.client = APIClient()

    def image_file(self, content=None):
        return SimpleUploadedFile(
            "product.png",
            content if content is not None else self.ONE_PIXEL_PNG,
            content_type="image/png",
        )

    def test_missing_image_returns_400(self):
        response = self.client.post(reverse("prompt-analysis"), {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)

    def test_non_image_upload_returns_400(self):
        upload = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")

        response = self.client.post(
            reverse("prompt-analysis"), {"image": upload}, format="multipart"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)

    @override_settings(PROVIDER_IMAGE_MAX_BYTES=67)
    def test_oversized_image_returns_400_with_chinese_message(self):
        response = self.client.post(
            reverse("prompt-analysis"),
            {"image": self.image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)
        self.assertIn("图片", str(response.data["image"][0]))

    @override_settings(VIDEO_PROVIDER_FORCE_MOCK=True)
    def test_mock_mode_returns_video_prompt_without_creating_jobs(self):
        response = self.client.post(
            reverse("prompt-analysis"),
            {"image": self.image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"prompt"})
        self.assertTrue(response.data["prompt"].strip())
        self.assertLessEqual(len(response.data["prompt"]), 2500)
        self.assertEqual(VideoJob.objects.count(), 0)
        self.assertEqual(ImageJob.objects.count(), 0)

    def test_analysis_error_returns_502(self):
        with patch(
            "videos.views.analyze_product_image",
            side_effect=PromptAnalysisError("provider unavailable"),
        ):
            response = self.client.post(
                reverse("prompt-analysis"),
                {"image": self.image_file()},
                format="multipart",
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data, {"detail": "provider unavailable"})


@override_settings(MEDIA_ROOT=MEDIA_ROOT, VIDEO_PROVIDER_FORCE_MOCK=True)
class ImageJobApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def image_file(self, name="product.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            content_type="image/png",
        )

    def test_create_requires_source_image(self):
        response = self.client.post(
            reverse("image-job-list"),
            {"provider": "aliyun", "prompt": "Generate a clean ecommerce hero image"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source_image", response.data)

    def test_create_rejects_unknown_provider(self):
        response = self.client.post(
            reverse("image-job-list"),
            {
                "provider": "unknown",
                "prompt": "Generate a clean ecommerce hero image",
                "source_image": self.image_file(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("provider", response.data)

    def test_create_submits_mock_image_job_and_lists_it(self):
        response = self.client.post(
            reverse("image-job-list"),
            {
                "provider": "seedream",
                "prompt": "Put the product on a premium studio background",
                "source_image": self.image_file(),
                "aspect_ratio": "1:1",
                "size": "2K",
                "count": 2,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "submitted")
        self.assertTrue(response.data["remote_task_id"].startswith("mock-image-"))

        list_response = self.client.get(reverse("image-job-list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data["results"]), 1)

    def test_detail_refresh_downloads_completed_image_result(self):
        job = ImageJob.objects.create(
            provider="aliyun",
            status="submitted",
            prompt="Create a polished product image",
            source_image=self.image_file(),
            remote_task_id="real-image-task-123",
        )

        class FinishedProvider:
            def submit(self, job):
                return {"status": "unused"}

            def refresh(self, job):
                return {
                    "status": ImageJob.Status.SUCCEEDED,
                    "result_urls": ["https://example.test/image.png"],
                    "raw_response": {"ok": True},
                }

        with patch("videos.image_providers.get_image_provider", return_value=FinishedProvider()):
            with patch("videos.services.download_image", return_value=Path(MEDIA_ROOT) / "images" / "demo.png") as download:
                response = self.client.get(reverse("image-job-detail", args=[job.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "succeeded")
        self.assertIn("images/demo.png", response.data["result_images"])
        download.assert_called_once()


@override_settings(
    ALIYUN_API_KEY="test-key",
    ALIYUN_IMAGE_MODEL="wan2.7-image",
    ALIYUN_BASE_URL="https://dashscope.aliyuncs.com/api/v1",
)
class ImageProviderTests(TestCase):
    def image_file(self, name="product.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            content_type="image/png",
        )

    def test_aliyun_wan_image_submit_uses_sync_multimodal_image_and_text(self):
        job = ImageJob.objects.create(
            provider="aliyun",
            prompt="生成高级感商品场景图",
            size="2K",
            count=2,
            source_image=self.image_file(),
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "output": {
                        "choices": [
                            {
                                "message": {
                                    "content": [
                                        {"image": "https://example.test/aliyun-result.png"}
                                    ]
                                }
                            }
                        ]
                    }
                }

        with patch("videos.image_providers.requests.post", return_value=Response()) as post:
            result = AliWanImageProvider().submit(job)

        payload = post.call_args.kwargs["json"]
        headers = post.call_args.kwargs["headers"]
        content = payload["input"]["messages"][0]["content"]
        self.assertEqual(result["status"], ImageJob.Status.SUCCEEDED)
        self.assertEqual(result["result_urls"], ["https://example.test/aliyun-result.png"])
        self.assertNotIn("X-DashScope-Async", headers)
        self.assertEqual(payload["model"], "wan2.7-image")
        self.assertTrue(content[0]["image"].startswith("data:image/png;base64,"))
        self.assertEqual(content[1]["text"], "生成高级感商品场景图")
        self.assertEqual(payload["parameters"]["n"], 2)

    @override_settings(
        VOLCENGINE_API_KEY="test-key",
        VOLCENGINE_BASE_URL="https://ark.cn-beijing.volces.com/api/v3",
        SEEDREAM_IMAGE_MODEL="doubao-seedream-4-5-251128",
    )
    def test_seedream_submit_sends_image_to_volcengine_images_endpoint(self):
        job = ImageJob.objects.create(
            provider="seedream",
            prompt="生成高级感商品场景图",
            size="2K",
            source_image=self.image_file(),
        )

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"id": "seedream-1", "data": [{"url": "https://example.test/result.png"}]}

        with patch("videos.image_providers.requests.post", return_value=Response()) as post:
            result = SeedreamImageProvider().submit(job)

        payload = post.call_args.kwargs["json"]
        self.assertEqual(result["status"], ImageJob.Status.SUCCEEDED)
        self.assertEqual(result["result_urls"], ["https://example.test/result.png"])
        self.assertEqual(payload["model"], "doubao-seedream-4-5-251128")
        self.assertTrue(payload["image"].startswith("data:image/png;base64,"))
        self.assertEqual(post.call_args.args[0], "https://ark.cn-beijing.volces.com/api/v3/images/generations")
