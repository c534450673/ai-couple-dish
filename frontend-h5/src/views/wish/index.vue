<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import { wishApi } from '@/api'
import AppTabbar from '@/components/AppTabbar.vue'

const activeTab = ref('all')
const wishList = ref([])
const showAddDialog = ref(false)
const refreshing = ref(false)
const isSkeleton = ref(true)

const addForm = ref({
  title: '',
  description: '',
  wishType: 'restaurant'
})

const wishTypes = [
  { value: 'restaurant', label: '餐厅', icon: 'shop-o', color: '#894c5c' },
  { value: 'dish', label: '菜品', icon: 'cart-o', color: '#c98a00' },
  { value: 'recipe', label: '食谱', icon: 'tv-o', color: '#5f7a4f' }
]

const getTypeIcon = (type) => {
  const map = { restaurant: 'shop-o', dish: 'cart-o', recipe: 'tv-o' }
  return map[type] || 'star-o'
}

const getTypeColor = (type) => {
  const map = { restaurant: '#894c5c', dish: '#c98a00', recipe: '#5f7a4f' }
  return map[type] || '#894c5c'
}

const loadWishList = async () => {
  try {
    const params = activeTab.value !== 'all' ? { status: activeTab.value } : {}
    const res = await wishApi.getWishList(params)
    wishList.value = res.data || []
  } catch (error) {
    showToast('加载失败')
  } finally {
    refreshing.value = false
    isSkeleton.value = false
  }
}

const onRefresh = () => {
  isSkeleton.value = true
  refreshing.value = true
  loadWishList()
}

const onTabChange = () => {
  wishList.value = []
  isSkeleton.value = true
  loadWishList()
}

const handleAdd = async () => {
  if (!addForm.value.title) {
    showToast('请输入心愿')
    return
  }

  try {
    await wishApi.addWish(addForm.value)
    showToast('添加成功')
    showAddDialog.value = false
    addForm.value = { title: '', description: '', wishType: 'restaurant' }
    onRefresh()
  } catch (error) {
    showToast('添加失败')
  }
}

const handleFulfill = async (item) => {
  try {
    await wishApi.fulfillWish(item.id)
    showToast('已实现')
    onRefresh()
  } catch (error) {
    showToast('操作失败')
  }
}

const handleUndo = async (item) => {
  try {
    await wishApi.unfulfillWish(item.id)
    showToast('已撤销')
    onRefresh()
  } catch (error) {
    showToast('操作失败')
  }
}

const handleDelete = async (item) => {
  try {
    await showConfirmDialog({ title: '确认删除', message: '确定要删除这个心愿吗？' })
    await wishApi.deleteWish(item.id)
    showToast('已删除')
    onRefresh()
  } catch (error) {
    if (error !== 'cancel') showToast('删除失败')
  }
}

onMounted(() => {
  loadWishList()
})
</script>

<template>
  <div class="wish-page">
    <header class="page-topbar">
      <span class="placeholder" />
      <h1 class="page-title">
        心愿单
      </h1>
      <button
        class="add"
        @click="showAddDialog = true"
      >
        <van-icon
          name="plus"
          size="20"
        />
      </button>
    </header>

    <!-- 心愿分类 -->
    <van-tabs
      v-model:active="activeTab"
      sticky
      offset-top="52"
      @change="onTabChange"
    >
      <van-tab
        title="全部"
        name="all"
      />
      <van-tab
        title="待实现"
        name="0"
      />
      <van-tab
        title="已实现"
        name="1"
      />
    </van-tabs>

    <van-pull-refresh
      v-model="refreshing"
      class="wish-body"
      @refresh="onRefresh"
    >
      <div v-if="isSkeleton">
        <div
          v-for="n in 3"
          :key="n"
          class="wish-card skeleton"
        >
          <div class="head">
            <div class="sk sk-icon" />
            <div class="info">
              <div class="sk sk-line sk-title" />
              <div class="sk sk-line sk-desc" />
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <div
          v-for="item in wishList"
          :key="item.id"
          class="wish-card"
        >
          <div class="head">
            <span
              class="type-ic"
              :style="{ background: getTypeColor(item.wishType) + '22', color: getTypeColor(item.wishType) }"
            >
              <van-icon
                :name="getTypeIcon(item.wishType)"
                size="20"
              />
            </span>
            <div class="info">
              <div class="title">
                {{ item.title }}
              </div>
              <div
                v-if="item.description"
                class="desc"
              >
                {{ item.description }}
              </div>
            </div>
            <van-tag
              :type="item.status === 1 ? 'success' : 'warning'"
              round
            >
              {{ item.status === 1 ? '已实现' : '待实现' }}
            </van-tag>
          </div>
          <div class="foot">
            <span class="time">{{ item.createTime }}</span>
            <div class="actions">
              <van-button
                v-if="item.status === 0"
                size="small"
                type="primary"
                round
                @click="handleFulfill(item)"
              >
                实现
              </van-button>
              <van-button
                v-if="item.status === 1"
                size="small"
                round
                @click="handleUndo(item)"
              >
                撤销
              </van-button>
              <van-button
                size="small"
                round
                @click="handleDelete(item)"
              >
                删除
              </van-button>
            </div>
          </div>
        </div>

        <van-empty
          v-if="wishList.length === 0"
          description="暂无心愿"
        >
          <van-button
            type="primary"
            round
            @click="showAddDialog = true"
          >
            添加心愿
          </van-button>
        </van-empty>
      </div>
    </van-pull-refresh>

    <!-- 添加心愿弹窗 -->
    <van-popup
      v-model:show="showAddDialog"
      position="bottom"
      round
    >
      <div class="add-dialog">
        <div class="dialog-header">
          <span>添加心愿</span>
          <van-icon
            name="cross"
            @click="showAddDialog = false"
          />
        </div>
        <div class="dialog-content">
          <van-field
            v-model="addForm.title"
            label="心愿"
            placeholder="想和TA一起做什么？"
          />
          <van-field
            v-model="addForm.description"
            type="textarea"
            label="描述"
            placeholder="详细描述..."
            rows="2"
          />
          <div class="type-select">
            <div
              v-for="type in wishTypes"
              :key="type.value"
              class="type-item"
              :class="{ active: addForm.wishType === type.value }"
              @click="addForm.wishType = type.value"
            >
              <van-icon
                :name="type.icon"
                size="24"
                :color="type.color"
              />
              <span>{{ type.label }}</span>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <van-button
            type="primary"
            block
            round
            @click="handleAdd"
          >
            保存
          </van-button>
        </div>
      </div>
    </van-popup>

    <app-tabbar />
  </div>
</template>

<style lang="scss" scoped>
.wish-page {
  min-height: 100vh;
  background: $color-background;
  padding-bottom: 96px;
}

.page-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $page-padding;
  @include glass(0.7);

  .placeholder,
  .add { width: 32px; }
  .add {
    border: none;
    background: transparent;
    color: $color-primary;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    cursor: pointer;
  }
  .page-title { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
}

.wish-body { padding: $space-4 $page-padding 0; }

.wish-card {
  @include card($radius-lg, $space-4);
  margin-bottom: $space-3;

  .head {
    display: flex;
    align-items: flex-start;
    gap: $space-3;

    .type-ic {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .info {
      flex: 1;
      .title { font-size: $fs-label; font-weight: $fw-medium; color: $color-on-surface; }
      .desc { font-size: $fs-caption; color: $color-on-surface-variant; margin-top: $space-1; @include ellipsis-lines(2); }
    }
  }

  .foot {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: $space-3;
    padding-top: $space-3;
    border-top: 1px solid $color-surface-high;

    .time { font-size: $fs-caption; color: $color-on-surface-variant; }
    .actions { display: flex; gap: $space-2; }
  }
}

.add-dialog {
  padding: $space-5;

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $space-4;
    span { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
    .van-icon { color: $color-on-surface-variant; }
  }

  .type-select {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $space-3;
    margin-top: $space-3;

    .type-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: $space-2;
      padding: $space-4 0;
      background: $color-surface-low;
      border-radius: $radius-md;
      transition: background $transition-base;

      &.active { background: $color-primary-fixed; }

      span { font-size: $fs-caption; color: $color-on-surface-variant; }
    }
  }

  .dialog-footer { margin-top: $space-4; }
}

// 骨架屏
.skeleton {
  pointer-events: none;
  .sk {
    background: linear-gradient(90deg, $color-surface-high 25%, $color-surface-low 50%, $color-surface-high 75%);
    background-size: 200% 100%;
    animation: sk-loading 1.5s infinite;
  }
  .head { display: flex; gap: $space-3; }
  .sk-icon { width: 40px; height: 40px; border-radius: 50%; }
  .info { flex: 1; }
  .sk-line { border-radius: 4px; }
  .sk-title { width: 55%; height: 15px; margin-bottom: 8px; }
  .sk-desc { width: 75%; height: 12px; }
}

@keyframes sk-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
