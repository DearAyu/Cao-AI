import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || '/api',
})

export interface PromptAnalysisResult {
  prompt: string
}

export interface PromptAssistantRequest {
  action?: 'generate' | 'revise'
  product_title: string
  product_detail: string
  selling_points?: string[]
  current_prompt?: string
  revision_instruction?: string
}

export interface PromptAssistantResult {
  selling_points: string[]
  prompt: string
}

export async function analyzePrompt(image: File): Promise<PromptAnalysisResult> {
  const form = new FormData()
  form.append('image', image)
  const response = await api.post<PromptAnalysisResult>('/prompt-analysis/', form)
  return response.data
}

export async function runPromptAssistant(payload: PromptAssistantRequest): Promise<PromptAssistantResult> {
  const response = await api.post<PromptAssistantResult>('/prompt-assistant/', payload)
  return response.data
}
