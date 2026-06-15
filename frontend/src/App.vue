<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
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

const videoProvider = ref<ProviderName>('aliyun')
const videoPrompt = ref('用柔和的摄影棚灯光展示商品，镜头缓慢推进，突出质感和跨境电商主图卖点。')
const videoAspectRatio = ref('1:1')
const videoDuration = ref(5)
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

const videoProviderOptions = [
  { label: '火山 Seedance', value: 'volcengine' },
  { label: '阿里万相', value: 'aliyun' },
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

const statusText: Record<string, string> = {
  pending: '等待提交',
  submitted: '已提交',
  processing: '生成中',
  succeeded: '已完成',
  failed: '失败',
}

const canGenerateVideo = computed(() => Boolean(videoImageFile.value) && !isSubmittingVideo.value)
const canGenerateImage = computed(() => Boolean(imageFile.value) && !isSubmittingImage.value)
const activeVideo = computed(() => currentVideoJob.value?.result_video_url || '')
const activeVideoImage = computed(() => videoImagePreview.value || currentVideoJob.value?.source_image_url || '')
const activeImagePreview = computed(() => imagePreview.value || currentImageJob.value?.source_image_url || '')
const activeGeneratedImages = computed(() => currentImageJob.value?.result_image_urls ?? [])
const historyItems = computed(() =>
  [
    ...videoJobs.value.map((job) => ({ kind: '视频', id: job.id, provider: job.provider_label, status: job.status, created_at: job.created_at })),
    ...imageJobs.value.map((job) => ({ kind: '图片', id: job.id, provider: job.provider_label, status: job.status, created_at: job.created_at })),
  ].sort((a, b) => b.created_at.localeCompare(a.created_at)),
)

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
  const [videoList, imageList] = await Promise.all([listVideoJobs(), listImageJobs()])
  videoJobs.value = videoList.results
  imageJobs.value = imageList.results
}

async function submitVideoJob() {
  if (!videoImageFile.value) return
  isSubmittingVideo.value = true
  try {
    currentVideoJob.value = await createVideoJob({
      provider: videoProvider.value,
      prompt: videoPrompt.value,
      aspect_ratio: videoAspectRatio.value,
      duration: videoDuration.value,
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
        colorPrimary: '#7657ff',
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
            <span>跨境图生视频</span>
          </div>
        </div>

        <nav class="nav">
          <button class="nav-item" :class="{ active: mode === 'video' }" @click="mode = 'video'">
            <RocketOutlined />视频生成
          </button>
          <button class="nav-item" :class="{ active: mode === 'image' }" @click="mode = 'image'">
            <FileImageOutlined />图片生成
          </button>
          <button class="nav-item" :class="{ active: mode === 'materials' }" @click="mode = 'materials'">
            <ProjectOutlined />商品素材
          </button>
          <button class="nav-item" :class="{ active: mode === 'history' }" @click="mode = 'history'">
            <HistoryOutlined />任务记录
          </button>
        </nav>
      </aside>

      <section class="workspace" v-if="mode === 'video'">
        <header class="topbar">
          <div>
            <p class="eyebrow">IMAGE TO VIDEO</p>
            <h1>图生视频工作台</h1>
            <p class="summary">上传商品图，选择火山 Seedance 或阿里万相，生成适合跨境电商展示的短视频。</p>
          </div>
          <a-button @click="loadJobs">刷新任务</a-button>
        </header>

        <div class="studio-grid">
          <section class="panel controls">
            <div class="panel-title"><span>视频参数</span></div>
            <label class="upload-zone">
              <input type="file" accept="image/*" @change="onVideoFileChange" />
              <img v-if="videoImagePreview" :src="videoImagePreview" alt="视频参考图" />
              <div v-else>
                <CloudUploadOutlined />
                <strong>上传商品图</strong>
                <span>PNG / JPG / WEBP</span>
              </div>
            </label>

            <a-form layout="vertical">
              <a-form-item label="厂商">
                <a-segmented v-model:value="videoProvider" block :options="videoProviderOptions" />
              </a-form-item>
              <a-form-item label="提示词">
                <a-textarea v-model:value="videoPrompt" :rows="4" :maxlength="500" show-count />
              </a-form-item>
              <div class="form-row">
                <a-form-item label="比例">
                  <a-select v-model:value="videoAspectRatio" :options="aspectRatioOptions" />
                </a-form-item>
                <a-form-item label="时长">
                  <a-select v-model:value="videoDuration" :options="[{ label: '5 秒', value: 5 }, { label: '10 秒', value: 10 }]" />
                </a-form-item>
              </div>
            </a-form>

            <a-button data-testid="generate-button" type="primary" size="large" block :disabled="!canGenerateVideo" :loading="isSubmittingVideo" @click="submitVideoJob">
              <PlayCircleOutlined />生成商品视频
            </a-button>
          </section>

          <section class="panel preview">
            <div class="panel-title">
              <span>生成监听</span>
              <a-tag v-if="currentVideoJob" :color="statusColor(currentVideoJob.status)">
                {{ statusText[currentVideoJob.status] }}
              </a-tag>
            </div>
            <div class="monitor">
              <video v-if="activeVideo" :src="activeVideo" controls />
              <img v-else-if="activeVideoImage" :src="activeVideoImage" alt="当前商品图" />
              <div v-else class="empty-monitor">
                <span class="scanline"></span>
                <strong>等待商品图</strong>
                <p>上传图片后，这里会显示原图、生成进度和最终视频。</p>
              </div>
            </div>
            <a-alert v-if="currentVideoJob?.status === 'failed'" type="error" show-icon :message="currentVideoJob.error_message || '生成失败'" />
            <div v-else-if="currentVideoJob && currentVideoJob.status !== 'succeeded'" class="progress-copy">
              <a-spin size="small" />
              <span>任务 {{ currentVideoJob.remote_task_id || currentVideoJob.id }} 正在处理，前端每 3 秒查询一次。</span>
            </div>
          </section>
        </div>

        <section class="panel jobs">
          <div class="panel-title"><span>最近视频任务</span><span class="muted">{{ videoJobs.length }} 条</span></div>
          <a-empty v-if="!videoJobs.length" description="暂无视频任务" />
          <div v-else class="job-list">
            <button v-for="job in videoJobs" :key="job.id" class="job-row" @click="selectVideoJob(job)">
              <span>#{{ job.id }}</span>
              <strong>{{ job.provider_label }}</strong>
              <span>{{ job.aspect_ratio }} / {{ job.duration }} 秒</span>
              <a-tag :color="statusColor(job.status)">{{ statusText[job.status] }}</a-tag>
            </button>
          </div>
        </section>
      </section>

      <section class="workspace" v-else-if="mode === 'image'">
        <header class="topbar">
          <div>
            <p class="eyebrow">IMAGE TO IMAGE</p>
            <h1>图片生成工作台</h1>
            <p class="summary">上传商品参考图，使用阿里 wan2.7-image 或字节 Doubao-Seedream-4.5 生成商品场景图。</p>
          </div>
          <a-button @click="loadJobs">刷新任务</a-button>
        </header>

        <div class="studio-grid">
          <section class="panel controls">
            <div class="panel-title"><span>图片参数</span></div>
            <label class="upload-zone">
              <input type="file" accept="image/*" @change="onImageFileChange" />
              <img v-if="imagePreview" :src="imagePreview" alt="图片参考图" />
              <div v-else>
                <CloudUploadOutlined />
                <strong>上传参考图</strong>
                <span>用于图生图，不会直接覆盖原图</span>
              </div>
            </label>

            <a-form layout="vertical">
              <a-form-item label="厂商">
                <a-segmented v-model:value="imageProvider" block :options="imageProviderOptions" />
              </a-form-item>
              <a-form-item label="提示词">
                <a-textarea v-model:value="imagePrompt" :rows="4" :maxlength="500" show-count />
              </a-form-item>
              <div class="form-row">
                <a-form-item label="比例">
                  <a-select v-model:value="imageAspectRatio" :options="aspectRatioOptions" />
                </a-form-item>
                <a-form-item label="清晰度">
                  <a-select v-model:value="imageSize" :options="[{ label: '1K', value: '1K' }, { label: '2K', value: '2K' }, { label: '4K', value: '4K' }]" />
                </a-form-item>
              </div>
              <a-form-item label="张数">
                <a-input-number v-model:value="imageCount" :min="1" :max="4" style="width: 100%" />
              </a-form-item>
            </a-form>

            <a-button data-testid="generate-image-button" type="primary" size="large" block :disabled="!canGenerateImage" :loading="isSubmittingImage" @click="submitImageJob">
              <FileImageOutlined />生成商品图片
            </a-button>
          </section>

          <section class="panel preview">
            <div class="panel-title">
              <span>图片预览</span>
              <a-tag v-if="currentImageJob" :color="statusColor(currentImageJob.status)">
                {{ statusText[currentImageJob.status] }}
              </a-tag>
            </div>
            <div class="monitor image-monitor">
              <div v-if="activeGeneratedImages.length" class="image-results">
                <img v-for="url in activeGeneratedImages" :key="url" :src="url" alt="生成结果图" />
              </div>
              <img v-else-if="activeImagePreview" :src="activeImagePreview" alt="当前参考图" />
              <div v-else class="empty-monitor">
                <span class="scanline"></span>
                <strong>等待参考图</strong>
                <p>上传参考图后，这里会显示原图和生成结果。</p>
              </div>
            </div>
            <a-alert v-if="currentImageJob?.status === 'failed'" type="error" show-icon :message="currentImageJob.error_message || '生成失败'" />
            <div v-else-if="currentImageJob && currentImageJob.status !== 'succeeded'" class="progress-copy">
              <a-spin size="small" />
              <span>任务 {{ currentImageJob.remote_task_id || currentImageJob.id }} 正在处理，前端每 3 秒查询一次。</span>
            </div>
          </section>
        </div>

        <section class="panel jobs">
          <div class="panel-title"><span>最近图片任务</span><span class="muted">{{ imageJobs.length }} 条</span></div>
          <a-empty v-if="!imageJobs.length" description="暂无图片任务" />
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
        <header class="topbar">
          <div>
            <p class="eyebrow">HISTORY</p>
            <h1>任务记录</h1>
            <p class="summary">汇总最近的视频和图片生成任务，方便快速回看状态。</p>
          </div>
          <a-button @click="loadJobs">刷新任务</a-button>
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
        <header class="topbar">
          <div>
            <p class="eyebrow">MATERIALS</p>
            <h1>商品素材</h1>
            <p class="summary">素材库先保留入口，下一版可以把上传图、生成图和视频统一归档。</p>
          </div>
        </header>
      </section>
    </main>
  </a-config-provider>
</template>
