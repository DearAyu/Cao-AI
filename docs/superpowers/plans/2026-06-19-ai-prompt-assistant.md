# AI Prompt Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact video-prompt toolbar with live character count, Doubao Seed 2.0 Pro image analysis, and a placeholder input-guide modal.

**Architecture:** A dedicated Django endpoint validates an uploaded image and delegates to a focused Volcengine multimodal provider that returns one video-oriented Chinese prompt. A new Vue component owns the editor toolbar and guide modal, while `App.vue` owns the selected image and async request so failed analysis cannot destroy existing text.

**Tech Stack:** Django 5, Django REST Framework, Requests, Vue 3, TypeScript, Ant Design Vue, Axios, Vitest, Vue Test Utils

**Working-tree constraint:** Preserve the user's existing uncommitted `App.vue` and `App.test.ts` changes. Do not stage or commit implementation changes.

---

### Task 1: Volcengine prompt-analysis provider

**Files:**
- Create: `backend/videos/prompt_analysis.py`
- Modify: `backend/videos/tests.py`
- Modify: `backend/cao_ai/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Add failing provider tests**

Add `import base64` and `from .prompt_analysis import PromptAnalysisError, analyze_product_image, extract_prompt`, then add this test class to `backend/videos/tests.py`:

```python
@override_settings(
    VIDEO_PROVIDER_FORCE_MOCK=False,
    VOLCENGINE_API_KEY="test-key",
    VOLCENGINE_BASE_URL="https://ark.cn-beijing.volces.com/api/v3",
    DOUBAO_SEED_MODEL="doubao-seed-2-0-pro-260215",
)
class PromptAnalysisProviderTests(TestCase):
    def image_file(self):
        return SimpleUploadedFile(
            "product.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            content_type="image/png",
        )

    def test_analysis_sends_configured_model_image_and_video_instruction(self):
        class Response:
            def json(self):
                return {
                    "choices": [
                        {"message": {"content": "柔和棚拍光下展示商品，镜头缓慢推进并突出材质细节。"}}
                    ]
                }

        with patch("videos.prompt_analysis.request_with_retries", return_value=Response()) as request:
            prompt = analyze_product_image(self.image_file())

        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "doubao-seed-2-0-pro-260215")
        self.assertEqual(payload["messages"][0]["content"][0]["type"], "image_url")
        self.assertTrue(
            payload["messages"][0]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")
        )
        self.assertIn("视频生成提示词", payload["messages"][0]["content"][1]["text"])
        self.assertEqual(prompt, "柔和棚拍光下展示商品，镜头缓慢推进并突出材质细节。")

    def test_analysis_rejects_missing_or_oversized_model_content(self):
        with self.assertRaisesMessage(PromptAnalysisError, "缺少提示词"):
            extract_prompt({"choices": []})

        with self.assertRaisesMessage(PromptAnalysisError, "超过 2500"):
            extract_prompt({"choices": [{"message": {"content": "字" * 2501}}]})
```

- [ ] **Step 2: Run the provider tests and verify RED**

Run: `.venv\Scripts\python.exe backend\manage.py test videos.tests.PromptAnalysisProviderTests`

Expected: ERROR because `videos.prompt_analysis` does not exist.

- [ ] **Step 3: Add model configuration**

Append to `.env.example`:

```dotenv
DOUBAO_SEED_MODEL=doubao-seed-2-0-pro-260215
```

Append near the Volcengine settings in `backend/cao_ai/settings.py`:

```python
DOUBAO_SEED_MODEL = os.getenv("DOUBAO_SEED_MODEL", "doubao-seed-2-0-pro-260215")
```

- [ ] **Step 4: Implement the provider**

Create `backend/videos/prompt_analysis.py`:

```python
import base64

from django.conf import settings

from .providers import ProviderError, raise_for_bad_response, request_with_retries


PROMPT_ANALYSIS_INSTRUCTION = (
    "分析商品图片，只输出一段中文视频生成提示词。描述商品主体、视觉卖点、棚拍灯光、"
    "镜头运动、节奏和构图；不要解释，不要加标题，内容不得超过 2500 字。"
)
MOCK_ANALYSIS_PROMPT = (
    "柔和棚拍光下展示商品主体，镜头缓慢推进并轻微环绕，突出材质、轮廓和包装细节，"
    "画面干净高级，节奏平稳，适合跨境电商主图视频。"
)


class PromptAnalysisError(Exception):
    pass


def image_data_url(uploaded_file) -> str:
    uploaded_file.seek(0)
    encoded = base64.b64encode(uploaded_file.read()).decode("ascii")
    uploaded_file.seek(0)
    content_type = uploaded_file.content_type or "image/jpeg"
    return f"data:{content_type};base64,{encoded}"


def extract_prompt(data: dict) -> str:
    choices = data.get("choices") or []
    content = choices[0].get("message", {}).get("content") if choices else None
    if isinstance(content, list):
        content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    prompt = content.strip() if isinstance(content, str) else ""
    if not prompt:
        raise PromptAnalysisError("模型返回中缺少提示词")
    if len(prompt) > 2500:
        raise PromptAnalysisError("模型返回的提示词超过 2500 字")
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
    try:
        response = request_with_retries(
            "post",
            f"{settings.VOLCENGINE_BASE_URL.rstrip('/')}/chat/completions",
            "Doubao prompt analysis",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.VOLCENGINE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        raise_for_bad_response(response, "Doubao prompt analysis")
        return extract_prompt(response.json())
    except ProviderError as exc:
        raise PromptAnalysisError(str(exc)) from exc
```

- [ ] **Step 5: Run the provider tests and verify GREEN**

Run: `.venv\Scripts\python.exe backend\manage.py test videos.tests.PromptAnalysisProviderTests`

Expected: both provider tests pass.

---

### Task 2: Prompt-analysis API and validation

**Files:**
- Create: `backend/videos/prompt_serializers.py`
- Modify: `backend/videos/views.py`
- Modify: `backend/videos/urls.py`
- Modify: `backend/videos/tests.py`

- [ ] **Step 1: Add failing endpoint tests**

Add this test class to `backend/videos/tests.py` using the same valid one-pixel PNG helper from Task 1:

```python
@override_settings(VIDEO_PROVIDER_FORCE_MOCK=True, PROVIDER_IMAGE_MAX_BYTES=2_000_000)
class PromptAnalysisApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def image_file(self, content_type="image/png"):
        return SimpleUploadedFile(
            "product.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            content_type=content_type,
        )

    def test_analysis_requires_an_image(self):
        response = self.client.post(reverse("prompt-analysis"), {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)

    def test_analysis_rejects_unsupported_file_type(self):
        response = self.client.post(
            reverse("prompt-analysis"),
            {"image": SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)

    def test_mock_analysis_returns_video_prompt(self):
        response = self.client.post(
            reverse("prompt-analysis"), {"image": self.image_file()}, format="multipart"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("镜头", response.data["prompt"])
        self.assertLessEqual(len(response.data["prompt"]), 2500)
```

- [ ] **Step 2: Run endpoint tests and verify RED**

Run: `.venv\Scripts\python.exe backend\manage.py test videos.tests.PromptAnalysisApiTests`

Expected: FAIL because the `prompt-analysis` URL is not registered.

- [ ] **Step 3: Implement upload validation**

Create `backend/videos/prompt_serializers.py`:

```python
from django.conf import settings
from rest_framework import serializers


class PromptAnalysisRequestSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, image):
        if image.size > settings.PROVIDER_IMAGE_MAX_BYTES:
            raise serializers.ValidationError(
                f"图片不能超过 {settings.PROVIDER_IMAGE_MAX_BYTES // 1_000_000} MB"
            )
        return image
```

- [ ] **Step 4: Implement and route the API view**

Add to `backend/videos/views.py`:

```python
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from .prompt_analysis import PromptAnalysisError, analyze_product_image
from .prompt_serializers import PromptAnalysisRequestSerializer


class PromptAnalysisView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PromptAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            prompt = analyze_product_image(serializer.validated_data["image"])
        except PromptAnalysisError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"prompt": prompt})
```

Update `backend/videos/urls.py`:

```python
from django.urls import path

from .views import ImageJobViewSet, PromptAnalysisView, VideoJobViewSet

urlpatterns = [
    path("prompt-analysis/", PromptAnalysisView.as_view(), name="prompt-analysis"),
    *router.urls,
]
```

- [ ] **Step 5: Run backend tests**

Run: `.venv\Scripts\python.exe backend\manage.py test videos`

Expected: all backend tests pass.

---

### Task 3: Reusable video prompt editor

**Files:**
- Create: `frontend/src/components/VideoPromptEditor.vue`
- Create: `frontend/src/components/VideoPromptEditor.test.ts`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Add failing component tests**

Create `frontend/src/components/VideoPromptEditor.test.ts`:

```ts
import { mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { afterEach, describe, expect, it } from 'vitest'
import VideoPromptEditor from './VideoPromptEditor.vue'

const mountEditor = (props: Record<string, unknown> = {}) =>
  mount(VideoPromptEditor, {
    props: { modelValue: '商品提示词', imageReady: false, analyzing: false, ...props },
    global: { plugins: [Antd] },
  })

describe('VideoPromptEditor', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('shows the live count and 2500 character limit', () => {
    const wrapper = mountEditor()

    expect(wrapper.get('[data-testid="prompt-count"]').text()).toBe('5 / 2500')
    expect(wrapper.get('textarea').attributes('maxlength')).toBe('2500')
  })

  it('enables analysis only when an image is ready and emits analyze', async () => {
    const disabled = mountEditor()
    expect(disabled.get('[data-testid="analyze-prompt"]').attributes('disabled')).toBeDefined()

    const ready = mountEditor({ imageReady: true })
    const button = ready.get('[data-testid="analyze-prompt"]')
    expect(button.attributes('disabled')).toBeUndefined()
    await button.trigger('click')
    expect(ready.emitted('analyze')).toHaveLength(1)
  })

  it('shows loading text while analysis is running', () => {
    const wrapper = mountEditor({ imageReady: true, analyzing: true })

    expect(wrapper.get('[data-testid="analyze-prompt"]').text()).toContain('分析中')
    expect(wrapper.get('[data-testid="analyze-prompt"]').attributes('disabled')).toBeDefined()
  })

  it('opens the placeholder input guide modal', async () => {
    const wrapper = mountEditor()
    await wrapper.get('[data-testid="open-prompt-guide"]').trigger('click')

    expect(document.body.textContent).toContain('输入向导')
    expect(document.body.textContent).toContain('向导内容将在后续版本中设计')
  })
})
```

- [ ] **Step 2: Run component tests and verify RED**

Run: `npm test -- VideoPromptEditor.test.ts`

Expected: FAIL because `VideoPromptEditor.vue` does not exist.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/VideoPromptEditor.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { BulbOutlined } from '@ant-design/icons-vue'

defineProps<{
  modelValue: string
  imageReady: boolean
  analyzing: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  analyze: []
  focus: []
}>()

const guideOpen = ref(false)
</script>

<template>
  <a-form-item label="提示词">
    <div class="video-prompt-editor">
      <a-textarea
        :value="modelValue"
        :rows="5"
        :maxlength="2500"
        :bordered="false"
        @update:value="emit('update:modelValue', $event)"
        @focus="emit('focus')"
      />
      <div class="video-prompt-toolbar">
        <a-button
          data-testid="analyze-prompt"
          size="small"
          type="primary"
          :loading="analyzing"
          :disabled="!imageReady || analyzing"
          @click="emit('analyze')"
        >
          {{ analyzing ? '分析中' : 'AI 分析' }}
        </a-button>
        <button
          class="prompt-guide-button"
          data-testid="open-prompt-guide"
          type="button"
          @click="guideOpen = true"
        >
          <BulbOutlined />
          <span>输入向导</span>
        </button>
        <span class="prompt-count" data-testid="prompt-count">{{ modelValue.length }} / 2500</span>
      </div>
    </div>
  </a-form-item>

  <a-modal v-model:open="guideOpen" title="输入向导">
    <p>向导内容将在后续版本中设计。</p>
    <template #footer>
      <a-button @click="guideOpen = false">关闭</a-button>
    </template>
  </a-modal>
</template>
```

- [ ] **Step 4: Add component styling**

Add to `frontend/src/style.css` near the existing prompt styles:

```css
.video-prompt-editor {
  overflow: hidden;
  border: 1px solid rgba(81, 64, 44, 0.2);
  border-radius: 8px;
  background: #fff;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.video-prompt-editor:focus-within {
  border-color: var(--violet);
  box-shadow: 0 0 0 2px rgba(111, 83, 232, 0.1);
}

.video-prompt-editor .ant-input {
  resize: vertical;
  box-shadow: none;
}

.video-prompt-toolbar {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 7px 10px;
  border-top: 1px solid rgba(81, 64, 44, 0.1);
}

.video-prompt-toolbar .ant-btn-sm {
  height: 26px;
  padding-inline: 9px;
  font-size: 12px;
}

.prompt-guide-button {
  height: 26px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0;
  border: 0;
  color: var(--ink);
  background: transparent;
  cursor: pointer;
  font-size: 12px;
}

.prompt-guide-button:hover {
  color: var(--violet-dark);
}

.prompt-count {
  margin-left: auto;
  color: #9a8b79;
  font-size: 12px;
  white-space: nowrap;
}
```

Add a mobile rule under `@media (max-width: 560px)` so controls cannot overlap:

```css
.video-prompt-toolbar {
  gap: 9px;
}
```

- [ ] **Step 5: Run component tests and verify GREEN**

Run: `npm test -- VideoPromptEditor.test.ts`

Expected: all editor component tests pass.

---

### Task 4: Frontend API and App integration

**Files:**
- Create: `frontend/src/api/promptAnalysis.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/App.test.ts`

- [ ] **Step 1: Add failing App integration tests**

Mock the new API at the top of `frontend/src/App.test.ts`:

```ts
import { analyzePrompt } from './api/promptAnalysis'

vi.mock('./api/promptAnalysis', () => ({ analyzePrompt: vi.fn() }))
```

Reset it in `beforeEach`, then add:

```ts
it('replaces the video prompt with AI analysis output', async () => {
  ;(analyzePrompt as Mock).mockResolvedValueOnce({ prompt: 'AI 反推的视频提示词' })
  const wrapper = mountApp()
  const input = wrapper.find('input[type="file"]')
  const file = new File(['image'], 'product.png', { type: 'image/png' })
  Object.defineProperty(input.element, 'files', { value: [file] })

  await input.trigger('change')
  await wrapper.get('[data-testid="analyze-prompt"]').trigger('click')
  await flushPromises()

  expect(analyzePrompt).toHaveBeenCalledWith(file)
  expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('AI 反推的视频提示词')
})

it('preserves the current prompt when AI analysis fails', async () => {
  ;(analyzePrompt as Mock).mockRejectedValueOnce(new Error('failed'))
  const wrapper = mountApp()
  const textarea = wrapper.get('textarea')
  await textarea.setValue('保留这段提示词')
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', {
    value: [new File(['image'], 'product.png', { type: 'image/png' })],
  })

  await input.trigger('change')
  await wrapper.get('[data-testid="analyze-prompt"]').trigger('click')
  await flushPromises()

  expect((textarea.element as HTMLTextAreaElement).value).toBe('保留这段提示词')
})
```

- [ ] **Step 2: Run App tests and verify RED**

Run: `npm test -- App.test.ts`

Expected: FAIL because `promptAnalysis.ts` and the analyze control do not exist.

- [ ] **Step 3: Add the typed API client**

Create `frontend/src/api/promptAnalysis.ts`:

```ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || '/api',
})

export interface PromptAnalysisResult {
  prompt: string
}

export async function analyzePrompt(image: File): Promise<PromptAnalysisResult> {
  const form = new FormData()
  form.append('image', image)
  const response = await api.post<PromptAnalysisResult>('/prompt-analysis/', form)
  return response.data
}
```

- [ ] **Step 4: Integrate analysis state and replacement into App**

Import `VideoPromptEditor` and `analyzePrompt` in `frontend/src/App.vue`, add:

```ts
const isAnalyzingPrompt = ref(false)

async function analyzeVideoPrompt() {
  if (!videoImageFile.value || isAnalyzingPrompt.value) return
  isAnalyzingPrompt.value = true
  try {
    const result = await analyzePrompt(videoImageFile.value)
    videoPrompt.value = result.prompt
    message.success('AI 分析完成')
  } catch {
    message.error('AI 分析失败，请检查模型配置后重试')
  } finally {
    isAnalyzingPrompt.value = false
  }
}
```

Replace the current prompt form item with:

```vue
<VideoPromptEditor
  v-model="videoPrompt"
  :image-ready="Boolean(videoImageFile)"
  :analyzing="isAnalyzingPrompt"
  @focus="onVideoPromptFocus"
  @analyze="analyzeVideoPrompt"
/>
```

- [ ] **Step 5: Run focused frontend tests**

Run: `npm test -- VideoPromptEditor.test.ts App.test.ts`

Expected: component and App integration tests pass.

---

### Task 5: Full verification and browser QA

**Files:**
- Verify all modified files from Tasks 1-4
- Keep implementation unstaged and uncommitted

- [ ] **Step 1: Run the complete backend suite**

Run: `.venv\Scripts\python.exe backend\manage.py test videos`

Expected: all backend tests pass with zero failures.

- [ ] **Step 2: Run the complete frontend suite**

Run: `npm test`

Working directory: `frontend`

Expected: all frontend tests pass with zero failures.

- [ ] **Step 3: Run the production build**

Run: `npm run build`

Working directory: `frontend`

Expected: TypeScript checking and Vite build complete with exit code 0.

- [ ] **Step 4: Restart local services and verify the API**

Restart Django on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`. With mock mode enabled, post a valid image to `/api/prompt-analysis/` and confirm HTTP 200 with a non-empty `prompt` no longer than 2500 characters.

- [ ] **Step 5: Verify desktop and mobile browser behavior**

At desktop width and at `590x912`, verify:

- The toolbar is inside the prompt editor without overlap.
- The counter reads `current / 2500` and updates while typing.
- AI analysis is gray and disabled before upload, violet after upload, and locked while loading.
- Mock analysis replaces the prompt.
- Input guide opens and closes the placeholder modal.
- Existing first-focus clearing and preset buttons still work.
- Browser console has no errors.

- [ ] **Step 6: Review the working tree without committing**

Run: `git diff --check` and `git status --short`.

Expected: no whitespace errors; implementation files remain modified or untracked, with no staged changes and no implementation commit.
