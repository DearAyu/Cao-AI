import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import App from './App.vue'
import { listImageJobs } from './api/imageJobs'
import { listVideoJobs } from './api/videoJobs'

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
    expect(wrapper.text()).toContain('阿里万相')
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
