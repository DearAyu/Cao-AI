import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || '/api',
})

export type JobStatus = 'pending' | 'submitted' | 'processing' | 'succeeded' | 'failed'
export type ProviderName = 'volcengine' | 'aliyun'

export interface VideoJob {
  id: number
  provider: ProviderName
  provider_label: string
  model_name: string
  status: JobStatus
  prompt: string
  aspect_ratio: string
  duration: number
  resolution: string
  source_image_url: string
  source_asset_urls: Array<{
    url: string
    media_type: 'image' | 'video'
    original_name: string
    size: number
  }>
  remote_task_id: string
  result_video_url: string
  error_message: string
  created_at: string
  updated_at: string
}

export interface VideoJobList {
  results: VideoJob[]
}

export async function listVideoJobs(): Promise<VideoJobList> {
  const response = await api.get<VideoJobList>('/video-jobs/')
  return response.data
}

export async function getVideoJob(id: number): Promise<VideoJob> {
  const response = await api.get<VideoJob>(`/video-jobs/${id}/`)
  return response.data
}

export async function createVideoJob(payload: {
  provider: ProviderName
  model_name?: string
  prompt: string
  aspect_ratio: string
  duration: number
  resolution: string
  source_image: File
  source_files?: File[]
}): Promise<VideoJob> {
  const form = new FormData()
  form.append('provider', payload.provider)
  if (payload.model_name) form.append('model_name', payload.model_name)
  form.append('prompt', payload.prompt)
  form.append('aspect_ratio', payload.aspect_ratio)
  form.append('duration', String(payload.duration))
  form.append('resolution', payload.resolution)
  form.append('source_image', payload.source_image)
  for (const file of payload.source_files?.length ? payload.source_files : [payload.source_image]) {
    form.append('source_files', file)
  }
  const response = await api.post<VideoJob>('/video-jobs/', form)
  return response.data
}
