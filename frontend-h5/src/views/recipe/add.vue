<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { generateForm } from '@/api/ai'

const router = useRouter()

const form = ref({
  title: '',
  description: '',
  difficulty: '简单',
  cookingTime: '',
  servings: '2',
  ingredientsText: '',
  stepsText: ''
})

const submitting = ref(false)
const aiPrompt = ref('')
const showAiDialog = ref(false)

const handleAiFill = async () => {
  if (!aiPrompt.value.trim()) {
    showToast('请先描述想做的菜')
    return
  }
  showLoadingToast({ message: 'AI 生成中...', forbidClick: true })
  try {
    const res = await generateForm('recipe', aiPrompt.value.trim())
    closeToast()
    if (res.code === 200 && res.data?.data) {
      const d = res.data.data
      if (d.title) form.value.title = String(d.title)
      if (d.description) form.value.description = String(d.description)
      if (d.difficulty) form.value.difficulty = String(d.difficulty)
      if (d.cookingTime != null) form.value.cookingTime = String(d.cookingTime)
      if (d.servings != null) form.value.servings = String(d.servings)
      if (Array.isArray(d.ingredients)) {
        form.value.ingredientsText = d.ingredients
          .map(i => `${i.name || ''} ${i.amount || ''}`.trim())
          .filter(Boolean)
          .join('\n')
      }
      if (Array.isArray(d.steps)) {
        form.value.stepsText = d.steps
          .map((s, idx) => `${idx + 1}. ${s.content || ''}`)
          .join('\n')
      }
      showAiDialog.value = false
      showToast('已填入表单，请核对后保存')
    } else {
      showToast(res.message || 'AI 生成失败')
    }
  } catch {
    closeToast()
    showToast('AI 生成失败')
  }
}

const parseIngredients = () => {
  return form.value.ingredientsText
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const parts = line.split(/\s+/)
      return { name: parts[0] || line, amount: parts.slice(1).join(' ') || '' }
    })
}

const parseSteps = () => {
  return form.value.stepsText
    .split('\n')
    .map(line => line.replace(/^\d+\.\s*/, '').trim())
    .filter(Boolean)
    .map(content => ({ content }))
}

const handleSubmit = async () => {
  if (!form.value.title.trim()) {
    showToast('请输入菜谱标题')
    return
  }

  submitting.value = true
  showLoadingToast({ message: '保存中...', forbidClick: true })

  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/recipe/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        title: form.value.title,
        description: form.value.description,
        difficulty: form.value.difficulty,
        cookingTime: form.value.cookingTime ? Number(form.value.cookingTime) : null,
        servings: form.value.servings ? Number(form.value.servings) : 2,
        ingredients: parseIngredients(),
        steps: parseSteps(),
        publish: false
      })
    }).then(r => r.json())

    closeToast()
    if (res.code === 200) {
      showToast('菜谱创建成功')
      router.back()
    } else {
      showToast(res.message || '保存失败')
    }
  } catch {
    closeToast()
    showToast('保存失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="recipe-add-page">
    <header class="page-topbar">
      <button
        class="back"
        @click="$router.back()"
      >
        <van-icon
          name="arrow-left"
          size="20"
        />
      </button>
      <span class="title">创建菜谱</span>
      <i class="placeholder" />
    </header>

    <div class="form-content">
      <div class="ai-fill-bar">
        <van-button
          size="small"
          round
          plain
          type="primary"
          icon="fire-o"
          @click="showAiDialog = true"
        >
          AI 帮填
        </van-button>
      </div>

      <van-form @submit="handleSubmit">
        <van-cell-group inset>
          <van-field
            v-model="form.title"
            label="标题"
            placeholder="如：番茄炒蛋"
            required
          />
          <van-field
            v-model="form.description"
            label="描述"
            type="textarea"
            rows="2"
            placeholder="一句话介绍这道菜"
          />
          <van-field
            v-model="form.difficulty"
            label="难度"
            placeholder="简单/中等/困难"
          />
          <van-field
            v-model="form.cookingTime"
            label="时长(分)"
            type="digit"
          />
          <van-field
            v-model="form.servings"
            label="份量(人)"
            type="digit"
          />
          <van-field
            v-model="form.ingredientsText"
            label="食材"
            type="textarea"
            rows="4"
            placeholder="每行一种：番茄 2个"
          />
          <van-field
            v-model="form.stepsText"
            label="步骤"
            type="textarea"
            rows="5"
            placeholder="每行一步"
          />
        </van-cell-group>

        <div class="form-actions">
          <van-button
            block
            round
            type="primary"
            native-type="submit"
            :loading="submitting"
          >
            保存菜谱
          </van-button>
        </div>
      </van-form>
    </div>

    <van-dialog
      v-model:show="showAiDialog"
      title="AI 帮填菜谱"
      show-cancel-button
      confirm-button-text="生成"
      @confirm="handleAiFill"
    >
      <van-field
        v-model="aiPrompt"
        type="textarea"
        rows="3"
        placeholder="例如：想要一份适合约会的简单番茄炒蛋，20分钟搞定"
        style="padding: 12px 16px"
      />
    </van-dialog>
  </div>
</template>

<style lang="scss" scoped>
.recipe-add-page {
  min-height: 100vh;
  background: $color-background;
}

.page-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $page-padding;
  @include glass(0.7);

  .back, .placeholder { width: 32px; }
  .back {
    border: none;
    background: transparent;
    color: $color-on-surface;
    display: flex;
    align-items: center;
    cursor: pointer;
  }
  .title { font-size: $fs-title; font-weight: $fw-semibold; }
}

.form-content { padding: $space-4 0 $space-8; }

.ai-fill-bar {
  padding: 0 $page-padding $space-3;
  display: flex;
  justify-content: flex-end;
}

.form-actions { padding: $space-8 $page-padding 0; }
</style>
