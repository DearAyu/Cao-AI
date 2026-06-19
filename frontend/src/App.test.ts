import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import App from './App.vue'
import { listImageJobs } from './api/imageJobs'
import { analyzePrompt } from './api/promptAnalysis'
import { createVideoJob, listVideoJobs } from './api/videoJobs'

vi.mock('./api/videoJobs', () => ({
  createVideoJob: vi.fn(),
  listVideoJobs: vi.fn().mockResolvedValue({ results: [] }),
  getVideoJob: vi.fn(),
}))

vi.mock('./api/imageJobs', () => ({
  createImageJob: vi.fn(),
  listImageJobs: vi.fn().mockResolvedValue({ results: [] }),
  getImageJob: vi.fn(),
}))

vi.mock('./api/promptAnalysis', () => ({
  analyzePrompt: vi.fn(),
}))

describe('Cao AI workbench', () => {
  beforeEach(() => {
    ;(createVideoJob as Mock).mockClear()
    ;(analyzePrompt as Mock).mockReset()
    ;(listVideoJobs as Mock).mockResolvedValue({ results: [] })
    ;(listImageJobs as Mock).mockResolvedValue({ results: [] })
  })

  const mountApp = () =>
    mount(App, {
      global: {
        plugins: [Antd],
      },
    })

  it('renders video and image generation navigation', () => {
    const wrapper = mountApp()

    expect(wrapper.text()).toContain('Cao AI')
    expect(wrapper.text()).toContain('视频生成')
    expect(wrapper.text()).toContain('图片生成')
    expect(wrapper.text()).toContain('Doubao-Seedance-2.0-fast')
  })

  it('uses video model select and allows prompts up to 2500 characters', () => {
    const wrapper = mountApp()

    expect(wrapper.text()).toContain('视频模型')
    expect(wrapper.text()).toContain('Doubao-Seedance-2.0-fast')
    expect(wrapper.text()).not.toContain('视频厂商')
    expect(wrapper.text()).not.toContain('wanx2.1-i2v-turbo')
    const formLabels = wrapper.findAll('.ant-form-item-label label').map((label) => label.text())
    expect(formLabels).toContain('提示词')
    expect(formLabels).not.toContain('影棚提示词')
    expect(wrapper.find('textarea').attributes('maxlength')).toBe('2500')
  })

  it('clears the untouched default video prompt on first focus only', async () => {
    const wrapper = mountApp()
    const textarea = wrapper.find('textarea')

    expect((textarea.element as HTMLTextAreaElement).value).not.toBe('')
    await textarea.trigger('focus')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('')

    await textarea.setValue('用户输入的提示词')
    await textarea.trigger('blur')
    await textarea.trigger('focus')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('用户输入的提示词')
  })

  it('preserves edited content when the first focus occurs', async () => {
    const wrapper = mountApp()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('预先编辑的提示词')
    await textarea.trigger('focus')

    expect((textarea.element as HTMLTextAreaElement).value).toBe('预先编辑的提示词')
  })

  it('enables AI prompt analysis only after a video image is uploaded', async () => {
    const wrapper = mountApp()
    const analyzeButton = wrapper.get('[data-testid="analyze-prompt"]')

    expect(analyzeButton.attributes('disabled')).toBeDefined()

    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')

    expect(analyzeButton.attributes('disabled')).toBeUndefined()
  })

  it('analyzes the exact uploaded file and replaces the video prompt', async () => {
    const generatedPrompt = 'AI generated product video prompt'
    ;(analyzePrompt as Mock).mockResolvedValueOnce({ prompt: generatedPrompt })
    const wrapper = mountApp()
    const file = new File(['image'], 'product.png', { type: 'image/png' })
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')

    await wrapper.get('[data-testid="analyze-prompt"]').trigger('click')
    await flushPromises()

    expect(analyzePrompt).toHaveBeenCalledWith(file)
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(generatedPrompt)
  })

  it('preserves the current video prompt when AI analysis fails', async () => {
    ;(analyzePrompt as Mock).mockRejectedValueOnce(new Error('analysis failed'))
    const wrapper = mountApp()
    const existingPrompt = 'Keep this prompt unchanged'
    await wrapper.get('textarea').setValue(existingPrompt)
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')

    await wrapper.get('[data-testid="analyze-prompt"]').trigger('click')
    await flushPromises()

    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(existingPrompt)
  })

  it('prevents duplicate prompt analysis while a request is running', async () => {
    let resolveAnalysis!: (value: { prompt: string }) => void
    ;(analyzePrompt as Mock).mockReturnValueOnce(new Promise((resolve) => {
      resolveAnalysis = resolve
    }))
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')
    const analyzeButton = wrapper.get('[data-testid="analyze-prompt"]')

    await Promise.all([analyzeButton.trigger('click'), analyzeButton.trigger('click')])

    expect(analyzePrompt).toHaveBeenCalledTimes(1)
    expect(analyzeButton.attributes('disabled')).toBeDefined()

    resolveAnalysis({ prompt: 'Analysis complete' })
    await flushPromises()
  })

  it('submits the Volcengine model id instead of display label', async () => {
    ;(createVideoJob as Mock).mockResolvedValueOnce({
      id: 1,
      provider: 'volcengine',
      provider_label: '火山 Seedance',
      model_name: 'doubao-seedance-2-0-fast-260128',
      status: 'submitted',
      prompt: '',
      aspect_ratio: '1:1',
      duration: 5,
      resolution: '720p',
      source_image_url: '',
      remote_task_id: 'mock-video',
      result_video_url: '',
      error_message: '',
      created_at: '2026-06-16T00:00:00Z',
      updated_at: '2026-06-16T00:00:00Z',
    })
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })

    await input.trigger('change')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')

    expect(createVideoJob).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'volcengine',
      model_name: 'doubao-seedance-2-0-fast-260128',
    }))
  })

  it('submits 15 second duration and selected resolution', async () => {
    ;(createVideoJob as Mock).mockResolvedValueOnce({
      id: 3,
      provider: 'volcengine',
      provider_label: '火山 Seedance',
      model_name: 'doubao-seedance-2-0-fast-260128',
      status: 'submitted',
      prompt: '',
      aspect_ratio: '1:1',
      duration: 15,
      resolution: '480p',
      source_image_url: '',
      remote_task_id: 'mock-video-15s',
      result_video_url: '',
      error_message: '',
      created_at: '2026-06-16T00:00:00Z',
      updated_at: '2026-06-16T00:00:00Z',
    })
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })

    await input.trigger('change')
    const selects = wrapper.findAllComponents({ name: 'ASelect' })
    await selects[2].vm.$emit('update:value', 15)
    if (selects[3]) await selects[3].vm.$emit('update:value', '480p')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')

    expect(wrapper.text()).toContain('分辨率')
    expect(createVideoJob).toHaveBeenCalledWith(expect.objectContaining({
      duration: 15,
      resolution: '480p',
    }))
  })

  it('infers Aliyun provider from the wan2.7 video model', async () => {
    ;(createVideoJob as Mock).mockResolvedValueOnce({
      id: 2,
      provider: 'aliyun',
      provider_label: '阿里万相',
      model_name: 'wan2.7-i2v',
      status: 'submitted',
      prompt: '',
      aspect_ratio: '1:1',
      duration: 5,
      resolution: '720p',
      source_image_url: '',
      remote_task_id: 'mock-aliyun-video',
      result_video_url: '',
      error_message: '',
      created_at: '2026-06-16T00:00:00Z',
      updated_at: '2026-06-16T00:00:00Z',
    })
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })

    await input.trigger('change')
    await wrapper.findComponent({ name: 'ASelect' }).vm.$emit('update:value', 'wan2.7-i2v')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')

    expect(createVideoJob).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'aliyun',
      model_name: 'wan2.7-i2v',
    }))
  })

  it('renders the studio redesign structure', () => {
    const wrapper = mountApp()

    expect(wrapper.text()).toContain('商品影棚创作台')
    expect(wrapper.text()).toContain('创作流程')
    expect(wrapper.text()).toContain('影棚预览')
  })

  it('keeps video generate disabled until an image is selected', () => {
    const wrapper = mountApp()
    const button = wrapper.find('[data-testid="generate-button"]')

    expect(button.attributes('disabled')).toBeDefined()
  })

  it('shows image generation providers after switching workspace', async () => {
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')

    expect(wrapper.text()).toContain('阿里 wan2.7-image')
    expect(wrapper.text()).toContain('字节 Seedream 4.5')
    expect(wrapper.find('[data-testid="generate-image-button"]').attributes('disabled')).toBeDefined()
  })

  it('keeps navigation usable when image jobs response is malformed', async () => {
    ;(listImageJobs as Mock).mockResolvedValueOnce({} as never)
    const wrapper = mountApp()
    await flushPromises()

    await wrapper.findAll('.nav-item')[1].trigger('click')

    expect(wrapper.text()).toContain('商品场景图影棚')
    expect(wrapper.find('[data-testid="generate-image-button"]').exists()).toBe(true)
  })
})
