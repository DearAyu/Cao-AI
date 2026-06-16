import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import App from './App.vue'
import { listImageJobs } from './api/imageJobs'
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

describe('Cao AI workbench', () => {
  beforeEach(() => {
    ;(createVideoJob as Mock).mockClear()
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

  it('uses video model select and allows longer prompts', () => {
    const wrapper = mountApp()

    expect(wrapper.text()).toContain('视频模型')
    expect(wrapper.text()).toContain('Doubao-Seedance-2.0-fast')
    expect(wrapper.text()).not.toContain('视频厂商')
    expect(wrapper.text()).not.toContain('wanx2.1-i2v-turbo')
    expect(wrapper.find('textarea').attributes('maxlength')).toBe('1500')
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
