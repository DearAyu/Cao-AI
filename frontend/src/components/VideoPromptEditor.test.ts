import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { afterEach, describe, expect, it } from 'vitest'
import VideoPromptEditor from './VideoPromptEditor.vue'

const mountEditor = (props: Partial<{
  modelValue: string
  imageReady: boolean
  analyzing: boolean
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

  it('emits v-model updates and focus from the textarea', async () => {
    const wrapper = mountEditor()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('新的提示词')
    await textarea.trigger('focus')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['新的提示词'])
    expect(wrapper.emitted('focus')).toHaveLength(1)
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

  it('orders the footer actions as AI analysis then input guide', () => {
    const wrapper = mountEditor()
    const footerButtons = wrapper.findAll('.video-prompt-editor__footer button')

    expect(footerButtons[0].attributes('data-testid')).toBe('analyze-prompt')
    expect(footerButtons[1].attributes('data-testid')).toBe('open-prompt-guide')
  })

  it('shows a disabled loading action while analyzing', () => {
    const wrapper = mountEditor({ imageReady: true, analyzing: true })
    const analyzeButton = wrapper.get('[data-testid="analyze-prompt"]')

    expect(analyzeButton.attributes('disabled')).toBeDefined()
    expect(analyzeButton.text()).toContain('分析中')
    expect(analyzeButton.find('.ant-btn-loading-icon').exists()).toBe(true)
  })

  it('uses the Ant Design bulb icon and opens and closes the input guide', async () => {
    const wrapper = mountEditor()
    const guideButton = wrapper.get('[data-testid="open-prompt-guide"]')

    expect(guideButton.find('.anticon-bulb svg').exists()).toBe(true)
    await guideButton.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('输入向导')
    expect(document.body.textContent).toContain('向导内容将在后续版本中设计。')

    const closeButton = document.body.querySelector<HTMLButtonElement>('.ant-modal-close')
    expect(closeButton).not.toBeNull()
    closeButton?.click()
    await flushPromises()

    expect(document.body.querySelector<HTMLElement>('.ant-modal')?.style.display).toBe('none')
  })
})
