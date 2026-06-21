import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || '/api',
})

export interface PromptAnalysisResult {
  prompt: string
}

export interface PromptAssistantRequest {
  action?: 'generate' | 'revise'
  video_brief?: string
  product_title: string
  product_detail: string
  selling_points?: string[]
  current_prompt?: string
  revision_instruction?: string
  reference_image?: File | null
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
  if (payload.reference_image) {
    const form = new FormData()
    form.append('action', payload.action ?? 'generate')
    if (payload.video_brief) form.append('video_brief', payload.video_brief)
    form.append('product_title', payload.product_title)
    form.append('product_detail', payload.product_detail)
    for (const point of payload.selling_points ?? []) form.append('selling_points', point)
    if (payload.current_prompt) form.append('current_prompt', payload.current_prompt)
    if (payload.revision_instruction) form.append('revision_instruction', payload.revision_instruction)
    form.append('reference_image', payload.reference_image)
    const response = await api.post<PromptAssistantResult>('/prompt-assistant/', form)
    return response.data
  }
  const response = await api.post<PromptAssistantResult>('/prompt-assistant/', payload)
  return response.data
}
