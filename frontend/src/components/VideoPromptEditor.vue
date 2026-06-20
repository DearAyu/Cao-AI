<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { EditOutlined } from '@ant-design/icons-vue'
import { runPromptAssistant } from '../api/promptAnalysis'

defineProps<{
  modelValue: string
  imageReady: boolean
  analyzing: boolean
  isDefault?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  analyze: []
  focus: [event: FocusEvent]
  blur: [event: FocusEvent]
}>()

const guideOpen = ref(false)
const productTitle = ref('')
const productDetail = ref('')
const sellingPoints = ref<string[]>([])
const assistantPrompt = ref('')
const revisionInstruction = ref('')
const assistantLoading = ref(false)
const revisionLoading = ref(false)

async function generateAssistantPrompt() {
  if (!productTitle.value.trim() || !productDetail.value.trim()) {
    message.warning('请先填写商品标题和商品详情')
    return
  }
  assistantLoading.value = true
  try {
    const result = await runPromptAssistant({
      product_title: productTitle.value,
      product_detail: productDetail.value,
    })
    sellingPoints.value = result.selling_points
    assistantPrompt.value = result.prompt
    message.success('提示词已生成')
  } catch {
    message.error('提示词助手生成失败，请稍后重试')
  } finally {
    assistantLoading.value = false
  }
}

async function reviseAssistantPrompt() {
  if (!assistantPrompt.value.trim()) {
    message.warning('请先生成提示词')
    return
  }
  if (!revisionInstruction.value.trim()) {
    message.warning('请填写修改要求')
    return
  }
  revisionLoading.value = true
  try {
    const result = await runPromptAssistant({
      action: 'revise',
      product_title: productTitle.value,
      product_detail: productDetail.value,
      selling_points: sellingPoints.value,
      current_prompt: assistantPrompt.value,
      revision_instruction: revisionInstruction.value,
    })
    sellingPoints.value = result.selling_points
    assistantPrompt.value = result.prompt
    revisionInstruction.value = ''
    message.success('提示词已修改')
  } catch {
    message.error('提示词修改失败，请稍后重试')
  } finally {
    revisionLoading.value = false
  }
}

function applyAssistantPrompt() {
  if (!assistantPrompt.value.trim()) return
  emit('update:modelValue', assistantPrompt.value)
  guideOpen.value = false
  message.success('已应用到提示词')
}
</script>

<template>
  <a-form-item label="提示词" class="video-prompt-editor">
    <div class="video-prompt-editor__field">
      <a-textarea
        :value="modelValue"
        :class="{ 'video-prompt-editor__textarea--muted': isDefault }"
        :rows="5"
        :maxLength="2500"
        @update:value="emit('update:modelValue', $event)"
        @focus="emit('focus', $event)"
        @blur="emit('blur', $event)"
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
          {{ analyzing ? '反推中' : '图片反推' }}
        </a-button>
        <a-button
          type="text"
          size="small"
          class="video-prompt-editor__guide"
          data-testid="open-prompt-guide"
          @click="guideOpen = true"
        >
          <template #icon><EditOutlined /></template>
          提示词助手
        </a-button>
        <span class="video-prompt-editor__count">{{ isDefault ? 0 : modelValue.length }} / 2500</span>
      </div>
    </div>
  </a-form-item>

  <a-modal v-model:open="guideOpen" title="提示词助手" :footer="null" width="760px">
    <div class="prompt-assistant">
      <a-alert
        type="info"
        show-icon
        message="输入商品标题和详情，助手会先总结卖点，再按预设规则生成视频提示词。"
      />

      <a-form layout="vertical" class="prompt-assistant__form">
        <a-form-item label="商品标题" required>
          <a-input
            v-model:value="productTitle"
            placeholder="例如：法式复古针织开衫套装"
            :maxlength="300"
          />
        </a-form-item>
        <a-form-item label="商品详情" required>
          <a-textarea
            v-model:value="productDetail"
            placeholder="填写材质、颜色、适用场景、功能特点、目标人群等"
            :rows="4"
            :maxlength="3000"
            show-count
          />
        </a-form-item>
        <a-button type="primary" :loading="assistantLoading" @click="generateAssistantPrompt">
          生成视频提示词
        </a-button>
      </a-form>

      <div v-if="sellingPoints.length" class="prompt-assistant__section">
        <h4>商品卖点</h4>
        <div class="prompt-assistant__chips">
          <span v-for="point in sellingPoints" :key="point">{{ point }}</span>
        </div>
      </div>

      <div v-if="assistantPrompt" class="prompt-assistant__section">
        <div class="prompt-assistant__title-row">
          <h4>最终视频提示词</h4>
          <a-button type="primary" size="small" @click="applyAssistantPrompt">应用到提示词</a-button>
        </div>
        <a-textarea v-model:value="assistantPrompt" :rows="7" :maxlength="2500" show-count />
      </div>

      <div v-if="assistantPrompt" class="prompt-assistant__section">
        <h4>继续修改</h4>
        <div class="prompt-assistant__revision">
          <a-input
            v-model:value="revisionInstruction"
            placeholder="例如：加强镜头推进感，减少旁白，突出通勤场景"
            @press-enter="reviseAssistantPrompt"
          />
          <a-button :loading="revisionLoading" @click="reviseAssistantPrompt">按要求修改</a-button>
        </div>
      </div>
    </div>
  </a-modal>
</template>
