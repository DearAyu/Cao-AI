# Video Prompt Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the video prompt field label, length limit, and first-focus behavior without changing image generation or preset behavior.

**Architecture:** Keep the behavior local to the existing Vue `App.vue` component. Extract the initial prompt into a constant, track whether the initial focus has occurred with a component-local flag, and use a guarded focus handler so only untouched default content is cleared.

**Tech Stack:** Vue 3, TypeScript, Ant Design Vue, Vitest, Vue Test Utils

---

### Task 1: Video prompt field behavior

**Files:**
- Modify: `frontend/src/App.test.ts:43`
- Modify: `frontend/src/App.vue:31-33`
- Modify: `frontend/src/App.vue:154-160`
- Modify: `frontend/src/App.vue:396-398`

- [ ] **Step 1: Write failing component tests**

Replace the existing prompt-length assertion and add focused behavior tests:

```ts
it('labels the video prompt and allows up to 2500 characters', () => {
  const wrapper = mountApp()

  expect(wrapper.text()).toContain('提示词')
  expect(wrapper.text()).not.toContain('影棚提示词')
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
```

- [ ] **Step 2: Run the tests and verify the expected failures**

Run: `npm test -- App.test.ts`

Expected: FAIL because the label is still `影棚提示词`, `maxlength` is still `1500`, and focusing leaves the default prompt intact.

- [ ] **Step 3: Implement the minimal guarded first-focus behavior**

Update the prompt state and add the focus handler:

```ts
const DEFAULT_VIDEO_PROMPT = '用柔和的摄影棚灯光展示商品，镜头缓慢推进，突出质感和跨境电商主图卖点。'
const videoPrompt = ref(DEFAULT_VIDEO_PROMPT)
let hasFocusedVideoPrompt = false

function onVideoPromptFocus() {
  if (hasFocusedVideoPrompt) return
  hasFocusedVideoPrompt = true
  if (videoPrompt.value === DEFAULT_VIDEO_PROMPT) videoPrompt.value = ''
}
```

Update the template:

```vue
<a-form-item label="提示词">
  <a-textarea
    v-model:value="videoPrompt"
    :rows="5"
    :maxLength="2500"
    show-count
    @focus="onVideoPromptFocus"
  />
</a-form-item>
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `npm test -- App.test.ts`

Expected: all tests in `App.test.ts` pass with zero failures.

- [ ] **Step 5: Run full frontend verification**

Run: `npm test`

Expected: all frontend tests pass.

Run: `npm run build`

Expected: TypeScript checking and Vite production build complete with exit code 0.

- [ ] **Step 6: Verify in the running browser**

At `http://127.0.0.1:5173/`, confirm the video prompt label reads `提示词`, the counter supports 2500 characters, first focus clears the untouched default, and later focus preserves entered text.

- [ ] **Step 7: Commit the implementation**

```bash
git add frontend/src/App.vue frontend/src/App.test.ts docs/superpowers/plans/2026-06-19-video-prompt-input.md
git commit -m "feat: refine video prompt input"
```
