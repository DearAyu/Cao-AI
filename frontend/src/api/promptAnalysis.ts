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
