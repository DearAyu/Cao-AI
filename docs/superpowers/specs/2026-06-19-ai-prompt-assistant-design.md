# AI Prompt Assistant Design

## Goal

Enhance the video prompt editor with a compact embedded toolbar that shows the live character count, generates a video-oriented prompt from the uploaded product image, and opens a placeholder input-guide dialog.

## Scope

This feature applies only to the video creation workspace. Image generation prompts and the contents of the future input guide are out of scope.

## User Interface

The prompt editor keeps its 2500-character limit and gains a footer inside the textarea frame:

- `AI 分析` is a compact secondary button.
- `输入向导` uses the existing Ant Design `BulbOutlined` SVG icon followed by text.
- The live counter is right-aligned and rendered as `current / 2500`.

The AI button has three states:

- Disabled gray before a product image is uploaded.
- Active violet after an image is available.
- Disabled light-violet loading state labeled `分析中` while a request is running.

The input guide opens an Ant Design modal titled `输入向导`. Its body contains only placeholder copy explaining that guide content will be designed later, plus a close action.

## Frontend Architecture

Extract the prompt UI from `App.vue` into a focused `VideoPromptEditor.vue` component. The component receives the current prompt, whether an image is ready, and whether analysis is running. It emits prompt updates, an analyze request, and manages the placeholder guide modal locally.

Add `frontend/src/api/promptAnalysis.ts` with a typed multipart request that sends the selected image to `POST /api/prompt-analysis/` and returns `{ prompt: string }`.

`App.vue` owns the selected image and async request. On success it replaces the current prompt with the returned prompt. On failure it preserves the existing prompt and shows an Ant Design error message.

## Backend Architecture

Add a dedicated DRF endpoint at `POST /api/prompt-analysis/`. It accepts one multipart `image` field, validates that it is a supported image within the configured provider size limit, and returns a generated prompt without creating a database job.

Keep provider-specific code in a new prompt-analysis service module. In real-provider mode, it sends the image and a fixed instruction to the Volcengine Ark multimodal chat endpoint. The instruction asks for one concise Chinese video-generation prompt describing the product, visual selling points, studio lighting, camera motion, pacing, and composition, with no commentary around the prompt.

The model is configured through `DOUBAO_SEED_MODEL`, defaulting to the requested `doubao-seed-2-0-pro` identifier. This remains configurable because Ark accounts may use a dated model ID or endpoint ID. The existing `VOLCENGINE_API_KEY` and `VOLCENGINE_BASE_URL` settings are reused.

When `VIDEO_PROVIDER_FORCE_MOCK=true`, the endpoint returns a deterministic example prompt so the local workflow remains testable without sending the image externally.

## Data Flow

1. The user uploads a product image using the existing uploader.
2. The AI button becomes active.
3. Clicking it sends the selected image to the prompt-analysis endpoint and enters the loading state.
4. The backend analyzes the image with Doubao Seed 2.0 Pro and returns a video-oriented Chinese prompt.
5. The frontend replaces the editor contents with that prompt and updates the counter.
6. The user can edit the result normally before creating the video.

## Errors And Limits

- No image: the AI button remains disabled and no request is sent.
- Unsupported or oversized image: the endpoint returns HTTP 400 with a Chinese validation message.
- Missing provider credentials, provider rejection, timeout, or malformed model output: the endpoint returns a suitable error status and safe Chinese message.
- Frontend failures never clear or replace the existing prompt.
- A returned prompt longer than 2500 characters is rejected by the backend rather than silently truncating it.
- Repeated clicks are blocked while analysis is running.

## Testing

Frontend component tests cover the live counter, 2500-character limit, disabled/active/loading AI states, analyze emission, and placeholder guide modal. App integration tests cover successful replacement and failure preservation.

Backend tests cover missing files, invalid files, mock output, provider payload shape, configured model selection, provider errors, malformed output, and the 2500-character response limit. The full Django and frontend suites, production frontend build, and browser interaction flow must pass before completion.
