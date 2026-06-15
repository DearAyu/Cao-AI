import axios from 'axios'
import type { JobStatus } from './videoJobs'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api',
})

export type ImageProviderName = 'aliyun' | 'seedream'

export interface ImageJob {
  id: number
  provider: ImageProviderName
  provider_label: string
  status: JobStatus
  prompt: string
  aspect_ratio: string
  size: string
  count: number
  source_image_url: string
  remote_task_id: string
  result_images: string[]
  result_image_urls: string[]
  error_message: string
  created_at: string
  updated_at: string
}

export interface ImageJobList {
  results: ImageJob[]
}

export async function listImageJobs(): Promise<ImageJobList> {
  const response = await api.get<ImageJobList>('/image-jobs/')
  return response.data
}

export async function getImageJob(id: number): Promise<ImageJob> {
  const response = await api.get<ImageJob>(`/image-jobs/${id}/`)
  return response.data
}

export async function createImageJob(payload: {
  provider: ImageProviderName
  prompt: string
  aspect_ratio: string
  size: string
  count: number
  source_image: File
}): Promise<ImageJob> {
  const form = new FormData()
  form.append('provider', payload.provider)
  form.append('prompt', payload.prompt)
  form.append('aspect_ratio', payload.aspect_ratio)
  form.append('size', payload.size)
  form.append('count', String(payload.count))
  form.append('source_image', payload.source_image)
  const response = await api.post<ImageJob>('/image-jobs/', form)
  return response.data
}
