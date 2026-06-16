<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  CloudUploadOutlined,
  FileImageOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  ProjectOutlined,
  RocketOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
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

type WorkspaceMode = 'video' | 'image' | 'materials' | 'history'

const mode = ref<WorkspaceMode>('video')

const videoModel = ref('doubao-seedance-2-0-fast-260128')
const videoPrompt = ref('用柔和的摄影棚灯光展示商品，镜头缓慢推进，突出质感和跨境电商主图卖点。')
const videoAspectRatio = ref('1:1')
const videoDuration = ref(5)
const videoResolution = ref('720p')
const videoImageFile = ref<File | null>(null)
const videoImagePreview = ref('')
const currentVideoJob = ref<VideoJob | null>(null)
const videoJobs = ref<VideoJob[]>([])
const isSubmittingVideo = ref(false)

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

let videoPollTimer: number | undefined
let imagePollTimer: number | undefined

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

const videoPromptPresets = [
  '柔和棚拍光，镜头缓慢推进，突出商品材质和主图卖点。',
  '干净白底到高级场景的转场，适合跨境电商详情页首屏。',
  '模特手部轻触商品，镜头环绕展示尺寸、质感和包装细节。',
]

const imagePromptPresets = [
  '保留商品主体，生成高级棚拍场景，干净背景，柔和反射。',
  '生成跨境电商主图，突出产品轮廓，背景有轻微空间层次。',
  '为商品创建节日营销场景，保持主体真实，画面明亮精致。',
]

const statusText: Record<string, string> = {
  pending: '等待提交',
  submitted: '已提交',
  processing: '生成中',
  succeeded: '已完成',
  failed: '失败',
}

const canGenerateVideo = computed(() => Boolean(videoImageFile.value) && !isSubmittingVideo.value)
const canGenerateImage = computed(() => Boolean(imageFile.value) && !isSubmittingImage.value)
const activeResolutionOptions = computed(() => {
  if (videoModel.value === 'doubao-seedance-2-0-260128') return resolutionOptions
  return resolutionOptions.filter((option) => option.value !== '1080p')
})
const activeVideo = computed(() => currentVideoJob.value?.result_video_url || '')
const activeVideoImage = computed(() => videoImagePreview.value || currentVideoJob.value?.source_image_url || '')
const activeImagePreview = computed(() => imagePreview.value || currentImageJob.value?.source_image_url || '')
const activeGeneratedImages = computed(() => currentImageJob.value?.result_image_urls ?? [])
const totalJobs = computed(() => videoJobs.value.length + imageJobs.value.length)
const videoStatusLabel = computed(() => (currentVideoJob.value ? statusText[currentVideoJob.value.status] : '待上传'))
const imageStatusLabel = computed(() => (currentImageJob.value ? statusText[currentImageJob.value.status] : '待上传'))
const historyItems = computed(() =>
  [
    ...videoJobs.value.map((job) => ({ kind: '视频', id: job.id, provider: job.provider_label, status: job.status, created_at: job.created_at })),
    ...imageJobs.value.map((job) => ({ kind: '图片', id: job.id, provider: job.provider_label, status: job.status, created_at: job.created_at })),
  ].sort((a, b) => b.created_at.localeCompare(a.created_at)),
)

function providerForVideoModel(modelName: string): ProviderName {
  return modelName.startsWith('wan') ? 'aliyun' : 'volcengine'
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

function useVideoPreset(prompt: string) {
  videoPrompt.value = prompt
}

function useImagePreset(prompt: string) {
  imagePrompt.value = prompt
}

function statusColor(status: string) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'processing' || status === 'submitted') return 'processing'
  return 'default'
}

function onVideoFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  videoImageFile.value = file
  if (videoImagePreview.value) URL.revokeObjectURL(videoImagePreview.value)
  videoImagePreview.value = URL.createObjectURL(file)
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
  if (!videoImageFile.value) return
  isSubmittingVideo.value = true
  try {
    currentVideoJob.value = await createVideoJob({
      provider: providerForVideoModel(videoModel.value),
      model_name: videoModel.value,
      prompt: videoPrompt.value,
      aspect_ratio: videoAspectRatio.value,
      duration: videoDuration.value,
      resolution: videoResolution.value,
      source_image: videoImageFile.value,
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
  isSubmittingImage.value = true
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
    }
  } catch {
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
    if (job.status === 'succeeded' || job.status === 'failed') stopImagePolling()
  }, 3000)
}

function stopVideoPolling() {
  if (videoPollTimer) window.clearInterval(videoPollTimer)
  videoPollTimer = undefined
}

function stopImagePolling() {
  if (imagePollTimer) window.clearInterval(imagePollTimer)
  imagePollTimer = undefined
}

function selectVideoJob(job: VideoJob) {
  currentVideoJob.value = job
  if (job.status === 'submitted' || job.status === 'processing') startVideoPolling(job.id)
}

function selectImageJob(job: ImageJob) {
  currentImageJob.value = job
  if (job.status === 'submitted' || job.status === 'processing') startImagePolling(job.id)
}

onMounted(loadJobs)
onUnmounted(() => {
  stopVideoPolling()
  stopImagePolling()
  if (videoImagePreview.value) URL.revokeObjectURL(videoImagePreview.value)
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
          <span>今日工作台</span>
          <strong>{{ totalJobs }}</strong>
          <small>已载入任务</small>
        </div>
      </aside>

      <section class="workspace" v-if="mode === 'video'">
        <header class="hero">
          <div>
            <p class="eyebrow">IMAGE TO VIDEO / PRODUCT STUDIO</p>
            <h1>商品影棚创作台</h1>
            <p class="summary">把一张商品图推进到可交付的短视频：上传素材、套用影棚提示词、监听生成状态，然后回到最近任务继续迭代。</p>
          </div>
          <div class="hero-actions">
            <a-button @click="loadJobs">刷新任务</a-button>
            <a-button type="primary" :disabled="!canGenerateVideo" :loading="isSubmittingVideo" @click="submitVideoJob">
              <PlayCircleOutlined />生成视频
            </a-button>
          </div>
        </header>

        <section class="flow-strip" aria-label="创作流程">
          <div class="flow-heading">创作流程</div>
          <div><span>01</span><strong>导入商品图</strong><small>{{ videoImageFile ? '素材已就绪' : '等待上传' }}</small></div>
          <div><span>02</span><strong>设置镜头语言</strong><small>{{ videoAspectRatio }} / {{ videoDuration }} 秒 / {{ videoResolution }}</small></div>
          <div><span>03</span><strong>生成与回看</strong><small>{{ videoStatusLabel }}</small></div>
        </section>

        <div class="studio-grid">
          <section class="panel controls">
            <div class="panel-title">
              <span>创作参数</span>
              <small>视频模式</small>
            </div>
            <label class="upload-zone">
              <input type="file" accept="image/*" @change="onVideoFileChange" />
              <img v-if="videoImagePreview" :src="videoImagePreview" alt="视频参考图" />
              <div v-else>
                <CloudUploadOutlined />
                <strong>拖入或点击上传商品图</strong>
                <span>建议使用干净主图，PNG / JPG / WEBP</span>
              </div>
            </label>

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
              <a-form-item label="影棚提示词">
                <a-textarea v-model:value="videoPrompt" :rows="5" :maxLength="1500" show-count />
              </a-form-item>
              <div class="prompt-chips">
                <button v-for="prompt in videoPromptPresets" :key="prompt" type="button" @click="useVideoPreset(prompt)">
                  {{ prompt }}
                </button>
              </div>
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

          <section class="panel preview">
            <div class="panel-title">
              <span>影棚预览</span>
              <a-tag v-if="currentVideoJob" :color="statusColor(currentVideoJob.status)">
                {{ statusText[currentVideoJob.status] }}
              </a-tag>
              <a-tag v-else>待上传</a-tag>
            </div>
            <div class="monitor">
              <video v-if="activeVideo" :src="activeVideo" controls />
              <img v-else-if="activeVideoImage" :src="activeVideoImage" alt="当前商品图" />
              <div v-else class="empty-monitor">
                <span class="scanline"></span>
                <strong>等待商品图进入影棚</strong>
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

        <section class="panel jobs">
          <div class="panel-title"><span>最近视频任务</span><span class="muted">{{ videoJobs.length }} 条</span></div>
          <a-empty v-if="!videoJobs.length" description="暂无视频任务，上传商品图后开始第一条生成" />
          <div v-else class="job-list">
            <button v-for="job in videoJobs" :key="job.id" class="job-row" @click="selectVideoJob(job)">
              <span>#{{ job.id }}</span>
              <strong>{{ job.provider_label }}</strong>
              <span>{{ job.aspect_ratio }} / {{ job.duration }} 秒 / {{ job.resolution }}</span>
              <a-tag :color="statusColor(job.status)">{{ statusText[job.status] }}</a-tag>
            </button>
          </div>
        </section>
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

        <section class="flow-strip" aria-label="创作流程">
          <div class="flow-heading">创作流程</div>
          <div><span>01</span><strong>上传参考图</strong><small>{{ imageFile ? '素材已就绪' : '等待上传' }}</small></div>
          <div><span>02</span><strong>选择出图规格</strong><small>{{ imageAspectRatio }} / {{ imageSize }} / {{ imageCount }} 张</small></div>
          <div><span>03</span><strong>挑选结果</strong><small>{{ imageStatusLabel }}</small></div>
        </section>

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
              <div class="prompt-chips">
                <button v-for="prompt in imagePromptPresets" :key="prompt" type="button" @click="useImagePreset(prompt)">
                  {{ prompt }}
                </button>
              </div>
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

          <section class="panel preview">
            <div class="panel-title">
              <span>影棚预览</span>
              <a-tag v-if="currentImageJob" :color="statusColor(currentImageJob.status)">
                {{ statusText[currentImageJob.status] }}
              </a-tag>
              <a-tag v-else>待上传</a-tag>
            </div>
            <div class="monitor image-monitor">
              <div v-if="activeGeneratedImages.length" class="image-results">
                <img v-for="url in activeGeneratedImages" :key="url" :src="url" alt="生成结果图" />
              </div>
              <img v-else-if="activeImagePreview" :src="activeImagePreview" alt="当前参考图" />
              <div v-else class="empty-monitor">
                <span class="scanline"></span>
                <strong>等待参考图进入影棚</strong>
                <p>上传参考图后，这里会显示原图和生成结果。</p>
              </div>
            </div>
            <a-alert v-if="currentImageJob?.status === 'failed'" type="error" show-icon :message="currentImageJob.error_message || '生成失败'" />
            <div v-else-if="currentImageJob && currentImageJob.status !== 'succeeded'" class="progress-copy">
              <a-spin size="small" />
              <span>任务 {{ currentImageJob.remote_task_id || currentImageJob.id }} 正在处理，每 3 秒自动刷新。</span>
            </div>
          </section>
        </div>

        <section class="panel jobs">
          <div class="panel-title"><span>最近图片任务</span><span class="muted">{{ imageJobs.length }} 条</span></div>
          <a-empty v-if="!imageJobs.length" description="暂无图片任务，上传参考图后开始第一张生成" />
          <div v-else class="job-list">
            <button v-for="job in imageJobs" :key="job.id" class="job-row" @click="selectImageJob(job)">
              <span>#{{ job.id }}</span>
              <strong>{{ job.provider_label }}</strong>
              <span>{{ job.size }} / {{ job.count }} 张</span>
              <a-tag :color="statusColor(job.status)">{{ statusText[job.status] }}</a-tag>
            </button>
          </div>
        </section>
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
