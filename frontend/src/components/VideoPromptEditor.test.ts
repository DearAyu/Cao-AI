import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import VideoPromptEditor from './VideoPromptEditor.vue'
import { runPromptAssistant } from '../api/promptAnalysis'

vi.mock('../api/promptAnalysis', () => ({
  runPromptAssistant: vi.fn(),
}))

const mountEditor = (props: Partial<{
  modelValue: string
  imageReady: boolean
  analyzing: boolean
  isDefault: boolean
}> = {}) => mount(VideoPromptEditor, {
  attachTo: document.body,
  props: {
    modelValue: '',
    imageReady: false,
    analyzing: false,
    ...props,
  },
  global: {
    plugins: [Antd],
  },
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('VideoPromptEditor', () => {
  it('shows a live custom count and enforces the 2500 character limit', async () => {
    const wrapper = mountEditor({ modelValue: '镜头推进' })
    const textarea = wrapper.find('textarea')

    expect(textarea.attributes('rows')).toBe('5')
    expect(textarea.attributes('maxlength')).toBe('2500')
    expect(wrapper.find('.video-prompt-editor__count').text()).toBe('4 / 2500')
    expect(wrapper.find('.ant-input-data-count').exists()).toBe(false)

    await wrapper.setProps({ modelValue: '产品缓慢旋转' })
    expect(wrapper.find('.video-prompt-editor__count').text()).toBe('6 / 2500')
  })

  it('emits v-model updates, focus and blur from the textarea', async () => {
    const wrapper = mountEditor()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('新的提示词')
    await textarea.trigger('focus')
    await textarea.trigger('blur')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['新的提示词'])
    expect(wrapper.emitted('focus')).toHaveLength(1)
    expect(wrapper.emitted('blur')).toHaveLength(1)
  })

  it('renders default prompt text in muted gray state', () => {
    const wrapper = mountEditor({ modelValue: '默认提示说明', isDefault: true })
    const textarea = wrapper.find('textarea')

    expect(textarea.classes()).toContain('video-prompt-editor__textarea--muted')
    expect(wrapper.find('.video-prompt-editor__count').text()).toBe('0 / 2500')
  })

  it('disables the AI action without an image and activates it when ready', async () => {
    const wrapper = mountEditor()
    const analyzeButton = wrapper.get('[data-testid="analyze-prompt"]')

    expect(analyzeButton.attributes('disabled')).toBeDefined()
    expect(analyzeButton.classes()).toContain('video-prompt-editor__analyze--inactive')

    await wrapper.setProps({ imageReady: true })
    expect(analyzeButton.attributes('disabled')).toBeUndefined()
    expect(analyzeButton.classes()).toContain('video-prompt-editor__analyze--active')

    await analyzeButton.trigger('click')
    expect(wrapper.emitted('analyze')).toHaveLength(1)
  })

  it('orders the footer actions as image reverse prompt then prompt assistant', () => {
    const wrapper = mountEditor()
    const footerButtons = wrapper.findAll('.video-prompt-editor__footer button')

    expect(footerButtons[0].attributes('data-testid')).toBe('analyze-prompt')
    expect(footerButtons[1].attributes('data-testid')).toBe('open-prompt-guide')
  })

  it('shows a disabled loading action while analyzing', () => {
    const wrapper = mountEditor({ imageReady: true, analyzing: true })
    const analyzeButton = wrapper.get('[data-testid="analyze-prompt"]')

    expect(analyzeButton.attributes('disabled')).toBeDefined()
    expect(analyzeButton.text()).toContain('反推中')
    expect(analyzeButton.find('.ant-btn-loading-icon').exists()).toBe(true)
  })

  it('uses an edit icon and opens and closes the prompt assistant', async () => {
    const wrapper = mountEditor()
    const guideButton = wrapper.get('[data-testid="open-prompt-guide"]')

    expect(guideButton.find('.anticon-edit svg').exists()).toBe(true)
    await guideButton.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('提示词助手')
    expect(document.body.textContent).toContain('商品标题')
    expect(document.body.textContent).toContain('商品详情')

    const closeButton = document.body.querySelector<HTMLButtonElement>('.ant-modal-close')
    expect(closeButton).not.toBeNull()
    closeButton?.click()
    await flushPromises()

    expect(document.body.querySelector<HTMLElement>('.ant-modal')?.style.display).toBe('none')
  })

  it('generates and applies an assistant prompt', async () => {
    vi.mocked(runPromptAssistant).mockResolvedValueOnce({
      selling_points: ['轻薄', '百搭'],
      prompt: 'Generated video prompt',
    })
    const wrapper = mountEditor()

    await wrapper.get('[data-testid="open-prompt-guide"]').trigger('click')
    await flushPromises()

    const inputs = document.body.querySelectorAll<HTMLInputElement>('.prompt-assistant input')
    inputs[0].value = '法式针织开衫'
    inputs[0].dispatchEvent(new Event('input'))
    const detail = document.body.querySelector<HTMLTextAreaElement>('.prompt-assistant textarea')
    expect(detail).not.toBeNull()
    detail!.value = '柔软亲肤，适合通勤。'
    detail!.dispatchEvent(new Event('input'))
    await flushPromises()

    const buttons = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button'))
    buttons.find((button) => button.textContent?.includes('生成视频提示词'))?.click()
    await flushPromises()

    expect(Array.from(document.body.querySelectorAll<HTMLTextAreaElement>('textarea')).some((item) => item.value === 'Generated video prompt')).toBe(true)
    Array.from(document.body.querySelectorAll<HTMLButtonElement>('button'))
      .find((button) => button.textContent?.includes('应用到提示词'))
      ?.click()
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['Generated video prompt'])
  })
})
