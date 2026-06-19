<script setup lang="ts">
import { ref } from 'vue'
import { BulbOutlined } from '@ant-design/icons-vue'

defineProps<{
  modelValue: string
  imageReady: boolean
  analyzing: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  analyze: []
  focus: [event: FocusEvent]
}>()

const guideOpen = ref(false)
</script>

<template>
  <a-form-item label="提示词" class="video-prompt-editor">
    <div class="video-prompt-editor__field">
      <a-textarea
        :value="modelValue"
        :rows="5"
        :maxLength="2500"
        @update:value="emit('update:modelValue', $event)"
        @focus="emit('focus', $event)"
      />
      <div class="video-prompt-editor__footer">
        <a-button
          type="primary"
          size="small"
          :loading="analyzing"
          :disabled="!imageReady || analyzing"
          :class="[
            'video-prompt-editor__analyze',
            imageReady && !analyzing
              ? 'video-prompt-editor__analyze--active'
              : 'video-prompt-editor__analyze--inactive',
          ]"
          data-testid="analyze-prompt"
          @click="emit('analyze')"
        >
          {{ analyzing ? '分析中' : 'AI 分析' }}
        </a-button>
        <a-button
          type="text"
          size="small"
          class="video-prompt-editor__guide"
          data-testid="open-prompt-guide"
          @click="guideOpen = true"
        >
          <template #icon><BulbOutlined /></template>
          输入向导
        </a-button>
        <span class="video-prompt-editor__count">{{ modelValue.length }} / 2500</span>
      </div>
    </div>
  </a-form-item>

  <a-modal v-model:open="guideOpen" title="输入向导" :footer="null">
    <p>向导内容将在后续版本中设计。</p>
  </a-modal>
</template>
