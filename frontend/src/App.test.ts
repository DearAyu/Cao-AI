import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import App from './App.vue'
import { createImageJob, listImageJobs } from './api/imageJobs'
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
  runPromptAssistant: vi.fn(),
}))

describe('Cao AI workbench', () => {
  beforeEach(() => {
    ;(createVideoJob as Mock).mockClear()
    ;(createImageJob as Mock).mockReset()
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

  it('collapses and expands the desktop sidebar shell', async () => {
    const wrapper = mountApp()
    const toggle = wrapper.get('[data-testid="rail-collapse-toggle"]')

    expect(wrapper.get('.shell').classes()).not.toContain('rail-collapsed')
    expect(toggle.attributes('aria-expanded')).toBe('true')

    await toggle.trigger('click')

    expect(wrapper.get('.shell').classes()).toContain('rail-collapsed')
    expect(toggle.attributes('aria-expanded')).toBe('false')

    await toggle.trigger('click')

    expect(wrapper.get('.shell').classes()).not.toContain('rail-collapsed')
    expect(toggle.attributes('aria-expanded')).toBe('true')
  })

  it('opens and closes the mobile sidebar drawer', async () => {
    const wrapper = mountApp()

    expect(wrapper.get('.shell').classes()).not.toContain('rail-open')

    await wrapper.get('[data-testid="mobile-rail-open"]').trigger('click')

    expect(wrapper.get('.shell').classes()).toContain('rail-open')
    expect(wrapper.find('[data-testid="mobile-rail-scrim"]').exists()).toBe(true)

    await wrapper.get('[data-testid="mobile-rail-scrim"]').trigger('click')

    expect(wrapper.get('.shell').classes()).not.toContain('rail-open')
    expect(wrapper.find('[data-testid="mobile-rail-scrim"]').exists()).toBe(false)
  })

  it('closes the mobile drawer after selecting a navigation item', async () => {
    const wrapper = mountApp()

    await wrapper.get('[data-testid="mobile-rail-open"]').trigger('click')
    await wrapper.findAll('.nav-item')[1].trigger('click')

    expect(wrapper.get('.shell').classes()).not.toContain('rail-open')
    expect(wrapper.find('[data-testid="generate-image-button"]').exists()).toBe(true)
  })

  it('does not render prompt preset cards in either workspace', async () => {
    const wrapper = mountApp()

    expect(wrapper.find('.prompt-chips').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('柔和棚拍光，镜头缓慢推进')

    await wrapper.findAll('.nav-item')[1].trigger('click')

    expect(wrapper.find('.prompt-chips').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('保留商品主体，生成高级棚拍场景')
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

  it('clears the default video prompt on focus and restores it after empty blur', async () => {
    const wrapper = mountApp()
    const textarea = wrapper.find('textarea')

    expect((textarea.element as HTMLTextAreaElement).value).not.toBe('')
    await textarea.trigger('focus')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('')
    await textarea.trigger('blur')
    expect((textarea.element as HTMLTextAreaElement).value).toContain('输入视频中想要的主体动作场景')
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

    expect(wrapper.text()).toContain('TikTok带货视频创作平台')
    expect(wrapper.text()).toContain('生成结果')
  })

  it('does not render legacy recent task panels in either generation workspace', async () => {
    const wrapper = mountApp()

    expect(wrapper.text()).not.toContain('最近视频任务')

    await wrapper.findAll('.nav-item')[1].trigger('click')

    expect(wrapper.text()).not.toContain('最近图片任务')
  })

  it('shows detailed records and progress for the 10 most recent video jobs', async () => {
    const jobs = Array.from({ length: 12 }, (_, index) => {
      const id = 212 - index
      const status = index === 1 ? 'processing' : index === 2 ? 'failed' : 'succeeded'
      return {
        id,
        provider: 'volcengine',
        provider_label: '火山 Seedance',
        model_name: 'doubao-seedance-2-0-fast-260128',
        status,
        prompt: `最近视频提示词 ${id}`,
        aspect_ratio: '1:1',
        duration: 5,
        resolution: '720p',
        source_image_url: `/media/video-source-${id}.png`,
        source_asset_urls: [],
        remote_task_id: `recent-video-task-${id}`,
        result_video_url: status === 'succeeded' ? `/media/video-result-${id}.mp4` : '',
        error_message: status === 'failed' ? '供应商生成失败' : '',
        created_at: `2026-06-19T12:${String(59 - index).padStart(2, '0')}:00Z`,
        updated_at: `2026-06-19T12:${String(59 - index).padStart(2, '0')}:00Z`,
      }
    })
    ;(listVideoJobs as Mock).mockResolvedValueOnce({ results: jobs })
    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.text()).toContain('生成结果')
    expect(wrapper.findAll('.result-record')).toHaveLength(10)
    expect(wrapper.text()).toContain('recent-video-task-212')
    expect(wrapper.text()).toContain('recent-video-task-211')
    expect(wrapper.text()).toContain('recent-video-task-203')
    expect(wrapper.text()).not.toContain('recent-video-task-202')
    expect(wrapper.text()).toContain('供应商生成失败')
    expect(wrapper.find('[data-testid="video-generation-stage"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="video-result-failed"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('最近视频任务')
  })
  it('keeps video generate disabled until an image is selected', () => {
    const wrapper = mountApp()
    const button = wrapper.find('[data-testid="generate-button"]')

    expect(button.attributes('disabled')).toBeDefined()
  })

  it('allows selecting multiple image or video assets for a video job', async () => {
    ;(createVideoJob as Mock).mockResolvedValueOnce({
      id: 4,
      provider: 'volcengine',
      provider_label: '火山 Seedance',
      model_name: 'doubao-seedance-2-0-fast-260128',
      status: 'submitted',
      prompt: '',
      aspect_ratio: '1:1',
      duration: 5,
      resolution: '720p',
      source_image_url: '',
      source_asset_urls: [],
      remote_task_id: 'mock-video-assets',
      result_video_url: '',
      error_message: '',
      created_at: '2026-06-16T00:00:00Z',
      updated_at: '2026-06-16T00:00:00Z',
    })
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    const image = new File(['image'], 'product.png', { type: 'image/png' })
    const video = new File(['video'], 'motion.mp4', { type: 'video/mp4' })

    expect(input.attributes('multiple')).toBeDefined()
    expect(input.attributes('accept')).toContain('video/mp4')
    Object.defineProperty(input.element, 'files', { value: [image, video] })

    await input.trigger('change')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')

    expect(createVideoJob).toHaveBeenCalledWith(expect.objectContaining({
      source_image: image,
      source_files: [image, video],
    }))
    expect(wrapper.text()).toContain('2 / 3')
  })

  it('downloads a generated video through a browser blob URL without opening a tab', async () => {
    ;(createVideoJob as Mock).mockResolvedValueOnce({
      id: 5,
      provider: 'volcengine',
      provider_label: '火山 Seedance',
      model_name: 'doubao-seedance-2-0-fast-260128',
      status: 'succeeded',
      prompt: 'Video prompt',
      aspect_ratio: '1:1',
      duration: 5,
      resolution: '720p',
      source_image_url: '/media/source.png',
      source_asset_urls: [],
      remote_task_id: 'mock-video-download',
      result_video_url: '/media/results/job-5-mock.mp4',
      error_message: '',
      created_at: '2026-06-16T00:00:00Z',
      updated_at: '2026-06-16T00:00:00Z',
    })
    const videoBlob = new Blob(['video'], { type: 'video/mp4' })
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, blob: vi.fn().mockResolvedValue(videoBlob) })
    vi.stubGlobal('fetch', fetchMock)
    const createObjectUrl = vi.spyOn(URL, 'createObjectURL')
      .mockReturnValueOnce('blob:preview')
      .mockReturnValue('blob:video-download')
    const revokeObjectUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })

    await input.trigger('change')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-testid="download-video"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('/media/results/job-5-mock.mp4')
    expect(createObjectUrl).toHaveBeenLastCalledWith(videoBlob)
    expect(anchorClick).toHaveBeenCalledTimes(1)
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:video-download')

    wrapper.unmount()
    anchorClick.mockRestore()
    revokeObjectUrl.mockRestore()
    createObjectUrl.mockRestore()
    vi.unstubAllGlobals()
  })

  it('rejects more than three uploaded video assets before submitting', async () => {
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [
        new File(['1'], 'one.png', { type: 'image/png' }),
        new File(['2'], 'two.png', { type: 'image/png' }),
        new File(['3'], 'three.png', { type: 'image/png' }),
        new File(['4'], 'four.png', { type: 'image/png' }),
      ],
    })

    await input.trigger('change')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')

    expect(createVideoJob).not.toHaveBeenCalled()
  })

  it('rejects an oversized video asset before submitting', async () => {
    const wrapper = mountApp()
    const input = wrapper.find('input[type="file"]')
    const file = new File(['video'], 'large.mp4', { type: 'video/mp4' })
    Object.defineProperty(file, 'size', { value: 50 * 1024 * 1024 + 1 })
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')
    await wrapper.find('[data-testid="generate-button"]').trigger('click')

    expect(createVideoJob).not.toHaveBeenCalled()
  })

  it('shows image generation providers after switching workspace', async () => {
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')

    const imageModelSelectOptions = wrapper.findAllComponents({ name: 'ASelect' })[0].props('options')
    expect(imageModelSelectOptions).toEqual(expect.arrayContaining([
      expect.objectContaining({ label: '阿里 wan2.7-image', value: 'aliyun' }),
      expect.objectContaining({ label: '字节 Seedream 4.5', value: 'seedream' }),
      expect.objectContaining({ label: 'Image2模型', value: 'openai' }),
    ]))
    expect(wrapper.find('[data-testid="generate-image-button"]').attributes('disabled')).toBeDefined()
  })

  it('renders image model selection as a dropdown with Image2 and prompt helper behavior', async () => {
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')
    const formLabels = wrapper.findAll('.ant-form-item-label label').map((label) => label.text())
    const textarea = wrapper.find('textarea')

    expect(formLabels).toContain('图片选择')
    expect(formLabels).toContain('提示词')
    expect(formLabels).not.toContain('厂商')
    expect(formLabels).not.toContain('场景提示词')
    expect(wrapper.findAllComponents({ name: 'ASelect' })[0].props('options')).toEqual(expect.arrayContaining([
      expect.objectContaining({ label: 'Image2模型', value: 'openai' }),
    ]))
    expect(wrapper.findComponent({ name: 'ASegmented' }).exists()).toBe(false)
    expect((textarea.element as HTMLTextAreaElement).value).toBe('商品信息包含商品卖点、使用方式、销售地区、发布平台等生图效果将会更好')
    expect(textarea.attributes('style')).toContain('color: rgb(140, 140, 140)')

    await textarea.trigger('focus')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('')

    await textarea.trigger('blur')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('商品信息包含商品卖点、使用方式、销售地区、发布平台等生图效果将会更好')
  })

  it('submits Image2 provider without sending the helper text as the prompt', async () => {
    ;(createImageJob as Mock).mockResolvedValueOnce({
      id: 34,
      provider: 'openai',
      provider_label: 'Image2模型',
      status: 'submitted',
      prompt: '',
      aspect_ratio: '1:1',
      size: '2K',
      count: 1,
      source_image_url: '/media/source.png',
      remote_task_id: 'image-task-openai',
      result_images: [],
      result_image_urls: [],
      error_message: '',
      created_at: '2026-06-19T13:03:36Z',
      updated_at: '2026-06-19T13:03:36Z',
    })
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')
    const selects = wrapper.findAllComponents({ name: 'ASelect' })
    await selects[0].vm.$emit('update:value', 'openai')

    await wrapper.get('[data-testid="generate-image-button"]').trigger('click')

    expect(createImageJob).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'openai',
      prompt: '',
    }))
  })

  it('does not render a submitted image job as a generation result', async () => {
    ;(createImageJob as Mock).mockResolvedValueOnce({
      id: 31,
      provider: 'aliyun',
      provider_label: '阿里 wan2.7-image',
      status: 'submitted',
      prompt: '商品场景图',
      aspect_ratio: '1:1',
      size: '2K',
      count: 1,
      source_image_url: '/media/source.png',
      remote_task_id: 'image-task-31',
      result_images: [],
      result_image_urls: [],
      error_message: '',
      created_at: '2026-06-19T13:03:36Z',
      updated_at: '2026-06-19T13:03:36Z',
    })
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')

    await wrapper.get('[data-testid="generate-image-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="image-generation-stage"]').exists()).toBe(false)
    expect(wrapper.findAll('.result-record')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('image-task-31')
    expect(wrapper.find('.image-monitor').exists()).toBe(false)
  })
  it('shows a complete task detail sheet with every generated image', async () => {
    ;(createImageJob as Mock).mockResolvedValueOnce({
      id: 32,
      provider: 'seedream',
      provider_label: '字节 Seedream 4.5',
      status: 'succeeded',
      prompt: '保留商品主体，生成法式复古商品场景图',
      aspect_ratio: '1:1',
      size: '2K',
      count: 2,
      source_image_url: '/media/source-32.png',
      remote_task_id: 'image-task-32',
      result_images: ['result-1.png', 'result-2.png'],
      result_image_urls: ['/media/result-1.png', '/media/result-2.png'],
      error_message: '',
      created_at: '2026-06-19T13:13:49Z',
      updated_at: '2026-06-19T13:13:59Z',
    })
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')

    await wrapper.get('[data-testid="generate-image-button"]').trigger('click')
    await flushPromises()

    const detail = wrapper.get('[data-testid="image-result-detail"]')
    expect(detail.text()).toContain('字节 Seedream 4.5')
    expect(detail.text()).toContain('2K')
    expect(detail.text()).toContain('1:1')
    expect(detail.text()).toContain('image-task-32')
    expect(detail.text()).toContain('保留商品主体，生成法式复古商品场景图')
    expect(detail.findAll('.result-detail-card')).toHaveLength(2)
    expect(detail.find('[data-testid="download-all-images"]').exists()).toBe(true)
    expect(detail.find('[data-testid="reuse-image-settings"]').exists()).toBe(true)
    expect(wrapper.find('.image-monitor').exists()).toBe(false)
  })

  it('downloads a generated image through a browser blob URL', async () => {
    ;(createImageJob as Mock).mockResolvedValueOnce({
      id: 33,
      provider: 'aliyun',
      provider_label: '阿里 wan2.7-image',
      status: 'succeeded',
      prompt: '浏览器下载测试',
      aspect_ratio: '1:1',
      size: '2K',
      count: 1,
      source_image_url: '/media/source-33.png',
      remote_task_id: 'image-task-33',
      result_images: ['result-33.png'],
      result_image_urls: ['/media/result-33.png'],
      error_message: '',
      created_at: '2026-06-19T13:13:49Z',
      updated_at: '2026-06-19T13:13:59Z',
    })
    const imageBlob = new Blob(['image'], { type: 'image/png' })
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, blob: vi.fn().mockResolvedValue(imageBlob) })
    vi.stubGlobal('fetch', fetchMock)
    const createObjectUrl = vi.spyOn(URL, 'createObjectURL')
      .mockReturnValueOnce('blob:preview')
      .mockReturnValue('blob:download')
    const revokeObjectUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    const wrapper = mountApp()
    await wrapper.findAll('.nav-item')[1].trigger('click')
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['image'], 'product.png', { type: 'image/png' })],
    })
    await input.trigger('change')
    await wrapper.get('[data-testid="generate-image-button"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-testid="download-image-0"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('/media/result-33.png')
    expect(createObjectUrl).toHaveBeenLastCalledWith(imageBlob)
    expect(anchorClick).toHaveBeenCalledTimes(1)
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:download')

    wrapper.unmount()
    anchorClick.mockRestore()
    revokeObjectUrl.mockRestore()
    createObjectUrl.mockRestore()
    vi.unstubAllGlobals()
  })

  it('shows detailed records for only the 10 most recent final image jobs', async () => {
    const jobs = Array.from({ length: 12 }, (_, index) => {
      const id = 112 - index
      const status = index === 1 ? 'processing' : index === 2 ? 'failed' : 'succeeded'
      return {
        id,
        provider: 'aliyun',
        provider_label: '阿里 wan2.7-image',
        status,
        prompt: `最近任务提示词 ${id}`,
        aspect_ratio: '1:1',
        size: '2K',
        count: 1,
        source_image_url: `/media/source-${id}.png`,
        remote_task_id: `recent-image-task-${id}`,
        result_images: status === 'succeeded' ? [`result-${id}.png`] : [],
        result_image_urls: status === 'succeeded' ? [`/media/result-${id}.png`] : [],
        error_message: status === 'failed' ? '供应商生成失败' : '',
        created_at: `2026-06-19T12:${String(59 - index).padStart(2, '0')}:00Z`,
        updated_at: `2026-06-19T12:${String(59 - index).padStart(2, '0')}:00Z`,
      }
    })
    ;(listImageJobs as Mock).mockResolvedValueOnce({ results: jobs })
    const wrapper = mountApp()
    await flushPromises()

    await wrapper.findAll('.nav-item')[1].trigger('click')

    expect(wrapper.text()).toContain('生成结果')
    expect(wrapper.findAll('.result-record')).toHaveLength(10)
    expect(wrapper.text()).toContain('recent-image-task-112')
    expect(wrapper.text()).toContain('recent-image-task-102')
    expect(wrapper.text()).not.toContain('recent-image-task-111')
    expect(wrapper.text()).not.toContain('recent-image-task-101')
    expect(wrapper.text()).toContain('供应商生成失败')
    expect(wrapper.find('[data-testid="image-generation-stage"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="image-result-failed"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('最近图片任务')
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
