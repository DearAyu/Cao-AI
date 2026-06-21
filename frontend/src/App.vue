<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  CloudUploadOutlined,
  CopyOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileImageOutlined,
  FormOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  ProjectOutlined,
  RocketOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { analyzePrompt } from './api/promptAnalysis'
import {
  createImageJob,
  getImageJob,
  listImageJobs,
  type ImageJob,
  type ImageProviderName,
} from './api/imageJobs'
import {
  createVideoJob,
  getVideoJob,
  listVideoJobs,
  type ProviderName,
  type VideoJob,
} from './api/videoJobs'
import VideoPromptEditor from './components/VideoPromptEditor.vue'

type WorkspaceMode = 'video' | 'image' | 'materials' | 'history'
type VideoSourceKind = 'image' | 'video'
interface VideoSourceAsset {
  file: File
  previewUrl: string
  kind: VideoSourceKind
}

const VIDEO_SOURCE_MAX_FILES = 3
const VIDEO_SOURCE_MAX_BYTES = 50 * 1024 * 1024
const VIDEO_SOURCE_ACCEPT = 'image/png,image/jpeg,image/webp,video/mp4,video/quicktime,video/webm'
const VIDEO_SOURCE_ALLOWED_TYPES = new Set(VIDEO_SOURCE_ACCEPT.split(','))

const mode = ref<WorkspaceMode>('video')

const DEFAULT_VIDEO_PROMPT = '输入视频中想要的主体动作场景，使用 英文更准确。例如，"一个美女在展示身上的服装，镜头由远到近推进"等'
const videoModel = ref('doubao-seedance-2-0-fast-260128')
const videoPrompt = ref(DEFAULT_VIDEO_PROMPT)
const isVideoPromptDefault = computed(() => videoPrompt.value === DEFAULT_VIDEO_PROMPT)
const videoAspectRatio = ref('1:1')
const videoDuration = ref(5)
const videoResolution = ref('720p')
const videoSourceAssets = ref<VideoSourceAsset[]>([])
const currentVideoJob = ref<VideoJob | null>(null)
const videoJobs = ref<VideoJob[]>([])
const isSubmittingVideo = ref(false)
const isAnalyzingPrompt = ref(false)

const imageProvider = ref<ImageProviderName>('aliyun')
const imagePrompt = ref('保留商品主体，生成一张干净高级的跨境电商商品场景图，柔和棚拍光，白紫色科技感背景。')
const imageAspectRatio = ref('1:1')
const imageSize = ref('2K')
const imageCount = ref(1)
const imageFile = ref<File | null>(null)
const imagePreview = ref('')
const currentImageJob = ref<ImageJob | null>(null)
const imageJobs = ref<ImageJob[]>([])
const isSubmittingImage = ref(false)
const imageEstimatedProgress = ref(8)
const imageSubmissionStartedAt = ref('')

let videoPollTimer: number | undefined
let imagePollTimer: number | undefined
let imageProgressTimer: number | undefined
const videoModelOptions = [
  {
    label: 'Doubao-Seedance-2.0-fast',
    value: 'doubao-seedance-2-0-fast-260128',
    description: '速度更快，适合批量预览和快速验证镜头效果',
  },
  {
    label: 'Doubao-Seedance-2.0',
    value: 'doubao-seedance-2-0-260128',
    description: '质量更稳，适合最终成片和重点商品展示',
  },
  {
    label: '阿里万相 wan2.7-i2v',
    value: 'wan2.7-i2v',
    description: '万相 2.7 图生视频协议，适合使用更长时长和新媒体输入格式',
  },
]

const imageProviderOptions = [
  { label: '阿里 wan2.7-image', value: 'aliyun' },
  { label: '字节 Seedream 4.5', value: 'seedream' },
]

const aspectRatioOptions = [
  { label: '1:1', value: '1:1' },
  { label: '9:16', value: '9:16' },
  { label: '16:9', value: '16:9' },
]

const durationOptions = [
  { label: '5 秒', value: 5 },
  { label: '10 秒', value: 10 },
  { label: '15 秒', value: 15 },
]

const resolutionOptions = [
  { label: '480p', value: '480p' },
  { label: '720p', value: '720p' },
  { label: '1080p', value: '1080p' },
]

const statusText: Record<string, string> = {
  pending: '等待提交',
  submitted: '已提交',
  processing: '生成中',
  succeeded: '已完成',
  failed: '失败',
}

const videoSourceFiles = computed(() => videoSourceAssets.value.map((asset) => asset.file))
const primaryVideoSource = computed(() => videoSourceAssets.value[0] ?? null)
const promptAnalysisImage = computed(() => videoSourceAssets.value.find((asset) => asset.kind === 'image')?.file ?? null)
const videoImagePreview = computed(() => primaryVideoSource.value?.kind === 'image' ? primaryVideoSource.value.previewUrl : '')
const canGenerateVideo = computed(() => videoSourceAssets.value.length > 0 && !isSubmittingVideo.value)
const canGenerateImage = computed(() => Boolean(imageFile.value) && !isSubmittingImage.value)
const activeResolutionOptions = computed(() => {
  if (videoModel.value === 'doubao-seedance-2-0-260128') return resolutionOptions
  return resolutionOptions.filter((option) => option.value !== '1080p')
})
const activeVideo = computed(() => currentVideoJob.value?.result_video_url || '')
const activeVideoSource = computed(() => primaryVideoSource.value?.kind === 'video' ? primaryVideoSource.value.previewUrl : '')
const activeVideoImage = computed(() => {
  const imageAsset = videoSourceAssets.value.find((asset) => asset.kind === 'image')
  return imageAsset?.previewUrl || currentVideoJob.value?.source_image_url || ''
})
const finalImageJobs = computed(() => imageJobs.value.filter((job) => job.status === 'succeeded' || job.status === 'failed'))
const recentVideoJobs = computed(() => videoJobs.value.slice(0, 10))
const recentImageJobs = computed(() => finalImageJobs.value.slice(0, 10))
const totalJobs = computed(() => videoJobs.value.length + imageJobs.value.length)
const historyItems = computed(() =>
  [
    ...videoJobs.value.map((job) => ({ kind: '视频', id: job.id, provider: job.provider_label, status: job.status, created_at: job.created_at })),
    ...imageJobs.value.map((job) => ({ kind: '图片', id: job.id, provider: job.provider_label, status: job.status, created_at: job.created_at })),
  ].sort((a, b) => b.created_at.localeCompare(a.created_at)),
)

function providerForVideoModel(modelName: string): ProviderName {
  return modelName.startsWith('wan') ? 'aliyun' : 'volcengine'
}

function formatDateTime(value: string) {
  if (!value) return '正在创建任务'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

watch(videoModel, () => {
  if (!activeResolutionOptions.value.some((option) => option.value === videoResolution.value)) {
    videoResolution.value = '720p'
  }
})

function safeResults<T>(list: { results?: T[] } | unknown): T[] {
  if (list && typeof list === 'object' && Array.isArray((list as { results?: unknown }).results)) {
    return (list as { results: T[] }).results
  }
  return []
}

function onVideoPromptFocus() {
  if (videoPrompt.value === DEFAULT_VIDEO_PROMPT) videoPrompt.value = ''
}

function onVideoPromptBlur() {
  if (!videoPrompt.value.trim()) videoPrompt.value = DEFAULT_VIDEO_PROMPT
}

async function analyzeVideoPrompt() {
  if (!promptAnalysisImage.value || isAnalyzingPrompt.value) return
  isAnalyzingPrompt.value = true
  try {
    const result = await analyzePrompt(promptAnalysisImage.value)
    videoPrompt.value = result.prompt
    message.success('AI 分析完成')
  } catch {
    message.error('AI 分析失败，请稍后重试')
  } finally {
    isAnalyzingPrompt.value = false
  }
}

function statusColor(status: string) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'processing' || status === 'submitted') return 'processing'
  return 'default'
}

function onVideoFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (!files.length) return
  if (files.length > VIDEO_SOURCE_MAX_FILES) {
    message.error(`最多只能上传 ${VIDEO_SOURCE_MAX_FILES} 个素材`)
    input.value = ''
    return
  }
  const invalidType = files.find((file) => !VIDEO_SOURCE_ALLOWED_TYPES.has(file.type))
  if (invalidType) {
    message.error('仅支持 PNG/JPG/WEBP 图片和 MP4/MOV/WEBM 视频')
    input.value = ''
    return
  }
  const oversized = files.find((file) => file.size > VIDEO_SOURCE_MAX_BYTES)
  if (oversized) {
    message.error('单个素材不能超过 50MB')
    input.value = ''
    return
  }
  revokeVideoSourcePreviews()
  videoSourceAssets.value = files.map((file) => ({
    file,
    previewUrl: URL.createObjectURL(file),
    kind: file.type.startsWith('video/') ? 'video' : 'image',
  }))
  input.value = ''
}

function revokeVideoSourcePreviews() {
  for (const asset of videoSourceAssets.value) {
    URL.revokeObjectURL(asset.previewUrl)
  }
}

function onImageFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  imageFile.value = file
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imagePreview.value = URL.createObjectURL(file)
}

async function loadJobs() {
  try {
    const [videoList, imageList] = await Promise.all([listVideoJobs(), listImageJobs()])
    videoJobs.value = safeResults<VideoJob>(videoList)
    imageJobs.value = safeResults<ImageJob>(imageList)
  } catch {
    videoJobs.value = []
    imageJobs.value = []
  }
}

async function submitVideoJob() {
  if (!primaryVideoSource.value) return
  isSubmittingVideo.value = true
  try {
    currentVideoJob.value = await createVideoJob({
      provider: providerForVideoModel(videoModel.value),
      model_name: videoModel.value,
      prompt: videoPrompt.value,
      aspect_ratio: videoAspectRatio.value,
      duration: videoDuration.value,
      resolution: videoResolution.value,
      source_image: primaryVideoSource.value.file,
      source_files: videoSourceFiles.value,
    })
    videoJobs.value = [currentVideoJob.value, ...videoJobs.value.filter((item) => item.id !== currentVideoJob.value?.id)]
    message.success('视频任务已提交')
    startVideoPolling(currentVideoJob.value.id)
  } catch {
    message.error('视频提交失败，请检查后端服务和厂商配置')
  } finally {
    isSubmittingVideo.value = false
  }
}

async function submitImageJob() {
  if (!imageFile.value) return
  currentImageJob.value = null
  isSubmittingImage.value = true
  startImageProgress()
  try {
    currentImageJob.value = await createImageJob({
      provider: imageProvider.value,
      prompt: imagePrompt.value,
      aspect_ratio: imageAspectRatio.value,
      size: imageSize.value,
      count: imageCount.value,
      source_image: imageFile.value,
    })
    imageJobs.value = [currentImageJob.value, ...imageJobs.value.filter((item) => item.id !== currentImageJob.value?.id)]
    message.success('图片任务已提交')
    if (currentImageJob.value.status === 'submitted' || currentImageJob.value.status === 'processing') {
      startImagePolling(currentImageJob.value.id)
    } else {
      finishImageProgress(currentImageJob.value.status === 'succeeded')
    }
  } catch {
    stopImageProgress()
    message.error('图片提交失败，请检查后端服务和厂商配置')
  } finally {
    isSubmittingImage.value = false
  }
}

function startVideoPolling(id: number) {
  stopVideoPolling()
  videoPollTimer = window.setInterval(async () => {
    const job = await getVideoJob(id)
    currentVideoJob.value = job
    videoJobs.value = [job, ...videoJobs.value.filter((item) => item.id !== job.id)]
    if (job.status === 'succeeded' || job.status === 'failed') stopVideoPolling()
  }, 3000)
}

function startImagePolling(id: number) {
  stopImagePolling()
  imagePollTimer = window.setInterval(async () => {
    const job = await getImageJob(id)
    currentImageJob.value = job
    imageJobs.value = [job, ...imageJobs.value.filter((item) => item.id !== job.id)]
    if (job.status === 'succeeded' || job.status === 'failed') {
      stopImagePolling()
      finishImageProgress(job.status === 'succeeded')
    }
  }, 3000)
}

function startImageProgress() {
  stopImageProgress()
  imageEstimatedProgress.value = 8
  imageSubmissionStartedAt.value = new Date().toISOString()
  imageProgressTimer = window.setInterval(() => {
    const remaining = 95 - imageEstimatedProgress.value
    imageEstimatedProgress.value = Math.min(95, imageEstimatedProgress.value + Math.max(1, Math.ceil(remaining / 12)))
  }, 1500)
}

function stopImageProgress() {
  if (imageProgressTimer) window.clearInterval(imageProgressTimer)
  imageProgressTimer = undefined
}

function finishImageProgress(succeeded: boolean) {
  stopImageProgress()
  if (succeeded) imageEstimatedProgress.value = 100
}

function imageResultFileName(job: ImageJob, index: number) {
  return `cao-ai-task-${job.id}-result-${index + 1}.png`
}

function videoResultFileName(job: VideoJob) {
  return `cao-ai-video-task-${job.id}.mp4`
}

function videoJobSourceVideo(job: VideoJob) {
  return job.source_asset_urls?.find((asset) => asset.media_type === 'video')?.url || ''
}

function videoJobSourceImage(job: VideoJob) {
  return job.source_asset_urls?.find((asset) => asset.media_type === 'image')?.url || job.source_image_url || ''
}

async function downloadImage(job: ImageJob, url: string, index: number) {
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error(`Download failed: ${response.status}`)
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = imageResultFileName(job, index)
    anchor.rel = 'noopener'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(objectUrl)
  } catch {
    message.error(`结果 ${index + 1} 下载失败，请稍后重试`)
  }
}

async function downloadVideo(job: VideoJob) {
  if (!job.result_video_url) return
  try {
    const response = await fetch(job.result_video_url)
    if (!response.ok) throw new Error(`Download failed: ${response.status}`)
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = videoResultFileName(job)
    anchor.rel = 'noopener'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(objectUrl)
  } catch {
    message.error('视频下载失败，请稍后重试')
  }
}


async function downloadAllImages(job: ImageJob) {
  for (const [index, url] of job.result_image_urls.entries()) {
    await downloadImage(job, url, index)
  }
}

async function copyVideoTaskId(job: VideoJob) {
  const taskId = String(job.remote_task_id || job.id)
  try {
    await navigator.clipboard.writeText(taskId)
    message.success('任务 ID 已复制')
  } catch {
    message.error('复制失败，请手动复制任务 ID')
  }
}

async function copyImageTaskId(job: ImageJob) {
  const taskId = String(job.remote_task_id || job.id)
  try {
    await navigator.clipboard.writeText(taskId)
    message.success('任务 ID 已复制')
  } catch {
    message.error('复制失败，请手动复制任务 ID')
  }
}

function reuseVideoSettings(job: VideoJob) {
  videoModel.value = job.model_name || videoModel.value
  videoPrompt.value = job.prompt
  videoAspectRatio.value = job.aspect_ratio
  videoDuration.value = job.duration
  videoResolution.value = job.resolution
  message.success('视频参数已载入，可调整后再次生成')
}

function reuseImageSettings(job: ImageJob) {
  imageProvider.value = job.provider
  imagePrompt.value = job.prompt
  imageAspectRatio.value = job.aspect_ratio
  imageSize.value = job.size
  imageCount.value = job.count
  message.success('参数已载入，可调整后再次生成')
}

function stopVideoPolling() {
  if (videoPollTimer) window.clearInterval(videoPollTimer)
  videoPollTimer = undefined
}

function stopImagePolling() {
  if (imagePollTimer) window.clearInterval(imagePollTimer)
  imagePollTimer = undefined
}

onMounted(loadJobs)
onUnmounted(() => {
  stopVideoPolling()
  stopImagePolling()
  stopImageProgress()
  revokeVideoSourcePreviews()
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
})
</script>

<template>
  <a-config-provider
    :theme="{
      token: {
        colorPrimary: '#6f53e8',
        borderRadius: 8,
        fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
      },
    }"
  >
    <main class="shell">
      <aside class="rail">
        <div class="brand">
          <div class="brand-mark">C</div>
          <div>
            <strong>Cao AI</strong>
            <span>商品影棚系统</span>
          </div>
        </div>

        <nav class="nav" aria-label="工作区">
          <button class="nav-item" :class="{ active: mode === 'video' }" @click="mode = 'video'">
            <RocketOutlined />
            <span>视频生成</span>
            <small>Image to video</small>
          </button>
          <button class="nav-item" :class="{ active: mode === 'image' }" @click="mode = 'image'">
            <FileImageOutlined />
            <span>图片生成</span>
            <small>Image to image</small>
          </button>
          <button class="nav-item" :class="{ active: mode === 'materials' }" @click="mode = 'materials'">
            <ProjectOutlined />
            <span>商品素材</span>
            <small>Assets</small>
          </button>
          <button class="nav-item" :class="{ active: mode === 'history' }" @click="mode = 'history'">
            <HistoryOutlined />
            <span>任务记录</span>
            <small>History</small>
          </button>
        </nav>

        <div class="rail-card">
          <span>今日工作数</span>
          <strong>{{ totalJobs }}</strong>
          <small>已载入任务</small>
        </div>
      </aside>

      <section class="workspace" v-if="mode === 'video'">
        <header class="hero">
          <div>
            <p class="eyebrow">IMAGE TO VIDEO / PRODUCT STUDIO</p>
            <h1>TikTok带货视频创作平台</h1>
            <p class="summary">把商品素材推进到可交付的短视频：上传素材、设置提示词、监听生成状态，然后查看生成结果。</p>
          </div>
          <div class="hero-actions">
            <a-button @click="loadJobs">刷新任务</a-button>
            <a-button type="primary" :disabled="!canGenerateVideo" :loading="isSubmittingVideo" @click="submitVideoJob">
              <PlayCircleOutlined />生成视频
            </a-button>
          </div>
        </header>

        <div class="studio-grid">
          <section class="panel controls">
            <div class="panel-title">
              <span>创作参数</span>
              <small>视频模式</small>
            </div>
            <label class="upload-zone video-upload-zone">
              <input type="file" :accept="VIDEO_SOURCE_ACCEPT" multiple @change="onVideoFileChange" />
              <img v-if="videoImagePreview" :src="videoImagePreview" alt="视频参考图" />
              <div v-else>
                <CloudUploadOutlined />
                <strong>拖入或点击上传商品图</strong>
                <span>建议使用干净主图，PNG / JPG / WEBP</span>
              </div>
            </label>

            <p class="video-upload-rule">支持 PNG / JPG / WEBP 图片和 MP4 / MOV / WEBM 视频，最多 3 个，单文件不超过 50MB。</p>

            <div v-if="videoSourceAssets.length" class="asset-selection-list">
              <div class="asset-selection-head">
                <span>已选素材</span>
                <strong>{{ videoSourceAssets.length }} / 3</strong>
              </div>
              <div class="asset-selection-items">
                <article v-for="(asset, index) in videoSourceAssets" :key="asset.previewUrl" class="asset-selection-item">
                  <img v-if="asset.kind === 'image'" :src="asset.previewUrl" alt="上传图片素材" />
                  <video v-else :src="asset.previewUrl" muted playsinline />
                  <div>
                    <strong>{{ index + 1 }}. {{ asset.file.name }}</strong>
                    <span>{{ asset.kind === 'image' ? '图片' : '视频' }} / {{ (asset.file.size / 1024 / 1024).toFixed(1) }}MB</span>
                  </div>
                </article>
              </div>
            </div>

            <a-form layout="vertical">
              <a-form-item label="视频模型">
                <a-select v-model:value="videoModel">
                  <a-select-option v-for="model in videoModelOptions" :key="model.value" :value="model.value">
                    <div class="model-option">
                      <strong>{{ model.label }}</strong>
                      <span>{{ model.description }}</span>
                    </div>
                  </a-select-option>
                </a-select>
                <p class="field-hint">
                  {{ videoModelOptions.find((model) => model.value === videoModel)?.description }}
                </p>
              </a-form-item>
              <VideoPromptEditor
                v-model="videoPrompt"
                :image-ready="Boolean(promptAnalysisImage)"
                :analyzing="isAnalyzingPrompt"
                :is-default="isVideoPromptDefault"
                @focus="onVideoPromptFocus"
                @blur="onVideoPromptBlur"
                @analyze="analyzeVideoPrompt"
              />
              <div class="form-row">
                <a-form-item label="画面比例">
                  <a-select v-model:value="videoAspectRatio" :options="aspectRatioOptions" />
                </a-form-item>
                <a-form-item label="视频时长">
                  <a-select v-model:value="videoDuration" :options="durationOptions" />
                </a-form-item>
                <a-form-item label="分辨率">
                  <a-select v-model:value="videoResolution" :options="activeResolutionOptions" />
                </a-form-item>
              </div>
            </a-form>

            <a-button data-testid="generate-button" type="primary" size="large" block :disabled="!canGenerateVideo" :loading="isSubmittingVideo" @click="submitVideoJob">
              <PlayCircleOutlined />生成商品视频
            </a-button>
          </section>

          <section class="panel preview video-result-panel recent-results-panel">
            <div class="panel-title">
              <span>生成结果</span>
              <small>最近 {{ recentVideoJobs.length }} 条</small>
            </div>
            <a-empty v-if="!recentVideoJobs.length" class="video-result-empty" description="暂无生成结果，上传素材后开始第一条视频创作" />

            <div v-if="recentVideoJobs.length" class="result-record-list">
              <article
                v-for="job in recentVideoJobs"
                :key="job.id"
                class="result-record image-result-detail video-result-detail"
                :class="`result-record-${job.status}`"
                :data-testid="job.status === 'succeeded' ? 'video-result-detail' : ['pending', 'submitted', 'processing'].includes(job.status) ? 'video-generation-stage' : job.status === 'failed' ? 'video-result-failed' : undefined"
              >
                <header class="result-detail-header">
                  <div class="result-detail-identity">
                    <video v-if="videoJobSourceVideo(job)" :src="videoJobSourceVideo(job)" muted playsinline />
                    <img v-else-if="videoJobSourceImage(job)" :src="videoJobSourceImage(job)" alt="任务参考素材" />
                    <div v-else class="generation-thumb-placeholder"><PlayCircleOutlined /></div>
                    <div class="result-detail-heading">
                      <div class="generation-specs">
                        <span>模型：{{ job.model_name || job.provider_label }}</span>
                        <i></i>
                        <span>分辨率：{{ job.resolution }}</span>
                        <i></i>
                        <span>画面比例：{{ job.aspect_ratio }}</span>
                        <i></i>
                        <span>视频时长：{{ job.duration }} 秒</span>
                      </div>
                      <div class="generation-subline">{{ formatDateTime(job.created_at) }} / 任务 ID：{{ job.remote_task_id || job.id }}</div>
                      <span class="generation-badge" :class="`generation-badge-${job.status}`">商品视频 · {{ statusText[job.status] }}</span>
                    </div>
                  </div>
                  <div class="result-detail-actions">
                    <a-button
                      v-if="job.status === 'succeeded' && job.result_video_url"
                      data-testid="download-video"
                      @click="downloadVideo(job)"
                    >
                      <DownloadOutlined />下载视频
                    </a-button>
                    <a-button @click="copyVideoTaskId(job)"><CopyOutlined />复制任务 ID</a-button>
                    <a-button @click="reuseVideoSettings(job)"><FormOutlined />复用参数</a-button>
                  </div>
                </header>

                <div class="result-detail-context">
                  <section class="result-prompt-card">
                    <span>生成提示词</span>
                    <p>{{ job.prompt || '未填写提示词' }}</p>
                  </section>
                  <section class="result-source-card">
                    <div>
                      <span>原始参考素材</span>
                      <small>用于本次视频生成任务</small>
                    </div>
                    <video v-if="videoJobSourceVideo(job)" :src="videoJobSourceVideo(job)" controls muted />
                    <a v-else-if="videoJobSourceImage(job)" :href="videoJobSourceImage(job)" target="_blank" rel="noopener">
                      <img :src="videoJobSourceImage(job)" alt="原始参考素材" />
                    </a>
                  </section>
                </div>

                <section v-if="job.status === 'succeeded' && job.result_video_url" class="video-result-player">
                  <div class="result-gallery-heading">
                    <div><span>生成结果</span><small>共 1 条视频</small></div>
                    <a-tag color="success">生成完成</a-tag>
                  </div>
                  <video :src="job.result_video_url" controls />
                </section>

                <section v-else-if="['pending', 'submitted', 'processing'].includes(job.status)" class="record-generation-progress">
                  <div class="generation-orbit" aria-hidden="true"><PlayCircleOutlined /></div>
                  <div class="generation-progress-copy">
                    <strong>AI 视频生成中</strong>
                    <span>任务正在处理，每 3 秒自动刷新，完成后会显示最终视频。</span>
                  </div>
                  <div class="generation-progress-track" role="progressbar" aria-label="视频生成进度">
                    <span style="width: 38%"></span>
                  </div>
                </section>

                <a-alert v-else-if="job.status === 'failed'" type="error" show-icon :message="job.error_message || '生成失败'" />
              </article>
            </div>

            <div class="monitor">
              <video v-if="activeVideo" :src="activeVideo" controls />
              <video v-else-if="activeVideoSource" :src="activeVideoSource" controls muted />
              <img v-else-if="activeVideoImage" :src="activeVideoImage" alt="当前商品图" />
              <div v-else class="empty-monitor">
                <span class="scanline"></span>
                <strong>等待商品素材进入影棚</strong>
                <p>上传后会在这里查看原图、生成进度和最终视频。</p>
              </div>
            </div>
            <a-alert v-if="currentVideoJob?.status === 'failed'" type="error" show-icon :message="currentVideoJob.error_message || '生成失败'" />
            <div v-else-if="currentVideoJob && currentVideoJob.status !== 'succeeded'" class="progress-copy">
              <a-spin size="small" />
              <span>任务 {{ currentVideoJob.remote_task_id || currentVideoJob.id }} 正在处理，每 3 秒自动刷新。</span>
            </div>
          </section>
        </div>

      </section>

      <section class="workspace" v-else-if="mode === 'image'">
        <header class="hero">
          <div>
            <p class="eyebrow">IMAGE TO IMAGE / PRODUCT STILLS</p>
            <h1>商品场景图影棚</h1>
            <p class="summary">先保留商品真实主体，再用可控的场景、光线和比例生成电商主图、详情图或营销图。</p>
          </div>
          <div class="hero-actions">
            <a-button @click="loadJobs">刷新任务</a-button>
            <a-button type="primary" :disabled="!canGenerateImage" :loading="isSubmittingImage" @click="submitImageJob">
              <FileImageOutlined />生成图片
            </a-button>
          </div>
        </header>

        <div class="studio-grid">
          <section class="panel controls">
            <div class="panel-title">
              <span>创作参数</span>
              <small>图片模式</small>
            </div>
            <label class="upload-zone">
              <input type="file" accept="image/*" @change="onImageFileChange" />
              <img v-if="imagePreview" :src="imagePreview" alt="图片参考图" />
              <div v-else>
                <CloudUploadOutlined />
                <strong>上传商品参考图</strong>
                <span>用于图生图，不会直接覆盖原图</span>
              </div>
            </label>

            <a-form layout="vertical">
              <a-form-item label="厂商">
                <a-segmented v-model:value="imageProvider" block :options="imageProviderOptions" />
              </a-form-item>
              <a-form-item label="场景提示词">
                <a-textarea v-model:value="imagePrompt" :rows="5" :maxLength="1500" show-count />
              </a-form-item>
              <div class="form-row">
                <a-form-item label="画面比例">
                  <a-select v-model:value="imageAspectRatio" :options="aspectRatioOptions" />
                </a-form-item>
                <a-form-item label="清晰度">
                  <a-select v-model:value="imageSize" :options="[{ label: '1K', value: '1K' }, { label: '2K', value: '2K' }, { label: '4K', value: '4K' }]" />
                </a-form-item>
              </div>
              <a-form-item label="出图张数">
                <a-input-number v-model:value="imageCount" :min="1" :max="4" style="width: 100%" />
              </a-form-item>
            </a-form>

            <a-button data-testid="generate-image-button" type="primary" size="large" block :disabled="!canGenerateImage" :loading="isSubmittingImage" @click="submitImageJob">
              <FileImageOutlined />生成商品图片
            </a-button>
          </section>

          <section class="panel preview recent-results-panel">
            <div class="panel-title recent-results-title">
              <span>生成结果</span>
              <small>最近 {{ recentImageJobs.length }} 条</small>
            </div>

            <a-empty v-if="!recentImageJobs.length" description="暂无生成结果，上传参考图后开始第一张创作" />

            <div v-if="recentImageJobs.length" class="result-record-list">
              <article
                v-for="job in recentImageJobs"
                :key="job.id"
                class="result-record image-result-detail"
                :class="`result-record-${job.status}`"
                :data-testid="job.status === 'succeeded' ? 'image-result-detail' : job.status === 'failed' ? 'image-result-failed' : undefined"
              >
              <header class="result-detail-header">
                <div class="result-detail-identity">
                  <img v-if="job.source_image_url" :src="job.source_image_url" alt="任务参考图" />
                  <div v-else class="generation-thumb-placeholder"><FileImageOutlined /></div>
                  <div class="result-detail-heading">
                    <div class="generation-specs">
                      <span>模型：{{ job.provider_label }}</span>
                      <i></i>
                      <span>分辨率：{{ job.size }}</span>
                      <i></i>
                      <span>画面比例：{{ job.aspect_ratio }}</span>
                      <i></i>
                      <span>生成数量：{{ job.count }} 张</span>
                    </div>
                    <div class="generation-subline">{{ formatDateTime(job.created_at) }} / 任务 ID：{{ job.remote_task_id || job.id }}</div>
                    <span class="generation-badge" :class="`generation-badge-${job.status}`">商品场景图 · {{ statusText[job.status] }}</span>
                  </div>
                </div>
                <div class="result-detail-actions">
                  <a-button v-if="job.status === 'succeeded' && job.result_image_urls.length" data-testid="download-all-images" @click="downloadAllImages(job)"><DownloadOutlined />下载全部</a-button>
                  <a-button @click="copyImageTaskId(job)"><CopyOutlined />复制任务 ID</a-button>
                  <a-button data-testid="reuse-image-settings" @click="reuseImageSettings(job)"><FormOutlined />复用参数</a-button>
                </div>
              </header>

              <div class="result-detail-context">
                <section class="result-prompt-card">
                  <span>生成提示词</span>
                  <p>{{ job.prompt || '鏈～鍐欐彁绀鸿瘝' }}</p>
                </section>
                <section class="result-source-card">
                  <div>
                    <span>原始参考图</span>
                    <small>用于本次图生图任务</small>
                  </div>
                  <a v-if="job.source_image_url" :href="job.source_image_url" target="_blank" rel="noopener">
                    <img :src="job.source_image_url" alt="原始参考图" />
                  </a>
                </section>
              </div>

              <section v-if="job.status === 'succeeded' && job.result_image_urls.length" class="result-detail-gallery">
                <div class="result-gallery-heading">
                  <div><span>生成结果</span><small>共 {{ job.result_image_urls.length }} 张</small></div>
                  <a-tag color="success">生成完成</a-tag>
                </div>
                <div class="result-detail-grid">
                  <div v-for="(url, index) in job.result_image_urls" :key="url" class="result-detail-card">
                    <div class="result-card-title">
                      <span>结果 {{ String(index + 1).padStart(2, '0') }}</span>
                      <div>
                        <a :href="url" target="_blank" rel="noopener" aria-label="查看大图"><EyeOutlined /></a>
                        <button :data-testid="`download-image-${index}`" type="button" aria-label="下载图片" @click="downloadImage(job, url, index)"><DownloadOutlined /></button>
                      </div>
                    </div>
                    <a class="result-image-link" :href="url" target="_blank" rel="noopener">
                      <img :src="url" :alt="`生成结果 ${index + 1}`" />
                    </a>
                  </div>
                </div>
              </section>

              <section v-else-if="job.status === 'failed'" class="record-failure-detail">
                <a-alert type="error" show-icon :message="job.error_message || '生成失败，请复用参数后重试'" />
              </section>

              <section v-else class="record-failure-detail">
                <a-alert type="warning" show-icon message="任务已完成，但没有返回可展示的图片" />
              </section>
              </article>
            </div>
          </section>
        </div>
      </section>

      <section class="workspace" v-else-if="mode === 'history'">
        <header class="hero">
          <div>
            <p class="eyebrow">HISTORY / DELIVERY LOG</p>
            <h1>任务记录</h1>
            <p class="summary">把视频和图片任务放在同一张交付清单里，快速检查生成状态、厂商和创建时间。</p>
          </div>
          <div class="hero-actions">
            <a-button @click="loadJobs">刷新任务</a-button>
          </div>
        </header>
        <section class="panel jobs">
          <div class="panel-title"><span>全部任务</span><span class="muted">{{ historyItems.length }} 条</span></div>
          <a-empty v-if="!historyItems.length" description="暂无任务" />
          <div v-else class="job-list">
            <div v-for="item in historyItems" :key="`${item.kind}-${item.id}`" class="job-row">
              <span>#{{ item.id }}</span>
              <strong>{{ item.kind }} / {{ item.provider }}</strong>
              <span>{{ new Date(item.created_at).toLocaleString() }}</span>
              <a-tag :color="statusColor(item.status)">{{ statusText[item.status] }}</a-tag>
            </div>
          </div>
        </section>
      </section>

      <section class="workspace" v-else>
        <header class="hero">
          <div>
            <p class="eyebrow">MATERIALS / ASSET ROOM</p>
            <h1>商品素材</h1>
            <p class="summary">这里会成为素材归档入口：上传图、生成图、成片视频和常用提示词都可以统一管理。</p>
          </div>
        </header>
        <section class="panel placeholder-panel">
          <ProjectOutlined />
          <strong>素材库入口已保留</strong>
          <p>下一步可以把生成结果沉淀为商品素材卡片，支持筛选、复用和再次生成。</p>
        </section>
      </section>
    </main>
  </a-config-provider>
</template>
