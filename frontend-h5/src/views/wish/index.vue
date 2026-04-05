<template>
  <div class="wish-page">
    <van-nav-bar title="心愿单">
      <template #right>
        <van-icon name="plus" size="20" @click="showAddDialog = true" />
      </template>
    </van-nav-bar>

    <!-- 心愿分类 -->
    <van-tabs v-model:active="activeTab" sticky @change="onTabChange">
      <van-tab title="全部" name="all"></van-tab>
      <van-tab title="待实现" name="0"></van-tab>
      <van-tab title="已实现" name="1"></van-tab>
    </van-tabs>

    <!-- 下拉刷新 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <div class="wish-list">
        <!-- 骨架屏 -->
        <div v-if="isSkeleton" class="wish-list-inner">
          <div v-for="n in 3" :key="n" class="wish-item card skeleton-item">
            <div class="wish-header">
              <div class="skeleton-icon"></div>
              <div class="wish-info">
                <div class="skeleton-title"></div>
                <div class="skeleton-desc"></div>
              </div>
            </div>
            <div class="wish-footer">
              <div class="skeleton-time"></div>
              <div class="skeleton-actions"></div>
            </div>
          </div>
        </div>

        <div v-else class="wish-list-inner">
          <div v-for="item in wishList" :key="item.id" class="wish-item card">
            <div class="wish-header">
              <van-icon :name="getTypeIcon(item.wishType)" size="24" :color="getTypeColor(item.wishType)" />
              <div class="wish-info">
                <div class="wish-title">{{ item.title }}</div>
                <div class="wish-desc" v-if="item.description">{{ item.description }}</div>
              </div>
              <van-tag :type="item.status === 1 ? 'success' : 'warning'" size="small">
                {{ item.status === 1 ? '已实现' : '待实现' }}
              </van-tag>
            </div>
            <div class="wish-footer">
              <span class="wish-time">{{ item.createTime }}</span>
              <div class="wish-actions">
                <van-button size="small" type="primary" v-if="item.status === 0" @click="handleFulfill(item)">
                  实现
                </van-button>
                <van-button size="small" v-if="item.status === 1" @click="handleUndo(item)">
                  撤销
                </van-button>
                <van-button size="small" @click="handleDelete(item)">删除</van-button>
              </div>
            </div>
          </div>

          <van-empty v-if="wishList.length === 0" description="暂无心愿">
            <van-button type="primary" round @click="showAddDialog = true">添加心愿</van-button>
          </van-empty>
        </div>
      </div>
    </van-pull-refresh>

    <!-- 添加心愿弹窗 -->
    <van-popup v-model:show="showAddDialog" position="bottom" round>
      <div class="add-dialog">
        <div class="dialog-header">
          <span>添加心愿</span>
          <van-icon name="cross" @click="showAddDialog = false" />
        </div>
        <div class="dialog-content">
          <van-field v-model="addForm.title" label="心愿" placeholder="想和TA一起做什么？" />
          <van-field v-model="addForm.description" type="textarea" label="描述" placeholder="详细描述..." rows="2" />
          <div class="type-select">
            <div
              v-for="type in wishTypes"
              :key="type.value"
              class="type-item"
              :class="{ active: addForm.wishType === type.value }"
              @click="addForm.wishType = type.value"
            >
              <van-icon :name="type.icon" size="24" :color="type.color" />
              <span>{{ type.label }}</span>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <van-button type="primary" block round @click="handleAdd">保存</van-button>
        </div>
      </div>
    </van-popup>

    <van-tabbar route>
      <van-tabbar-item to="/home" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/menu" icon="shop-o">餐厅</van-tabbar-item>
      <van-tabbar-item to="/feed" icon="gift-o">投喂</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import { wishApi } from '@/api'

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
  { value: 'restaurant', label: '餐厅', icon: 'shop-o', color: '#ff4757' },
  { value: 'dish', label: '菜品', icon: 'cart-o', color: '#ffd93d' },
  { value: 'recipe', label: '食谱', icon: 'tv-o', color: '#56ab2f' }
]

const getTypeIcon = (type) => {
  const map = { restaurant: 'shop-o', dish: 'cart-o', recipe: 'tv-o' }
  return map[type] || 'star-o'
}

const getTypeColor = (type) => {
  const map = { restaurant: '#ff4757', dish: '#ffd93d', recipe: '#56ab2f' }
  return map[type] || '#999'
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
    await wishApi.fulfillWish(item.id)
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

<style lang="scss" scoped>
.wish-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 70px;
}

.wish-list {
  padding: 12px 16px;
}

.wish-list-inner {
  .wish-item {
    padding: 16px;
    margin-bottom: 12px;

    .wish-header {
      display: flex;
      align-items: flex-start;

      .wish-info {
        flex: 1;
        margin-left: 12px;

        .wish-title {
          font-size: 15px;
          font-weight: 500;
          color: #333;
        }

        .wish-desc {
          font-size: 13px;
          color: #999;
          margin-top: 4px;
        }
      }
    }

    .wish-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #f5f5f5;

      .wish-time {
        font-size: 12px;
        color: #999;
      }

      .wish-actions {
        display: flex;
        gap: 8px;
      }
    }
  }
}

.add-dialog {
  padding: 16px;

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    span {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .type-select {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 12px;

    .type-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 12px;

      &.active {
        background: #fff0f3;
      }

      span {
        font-size: 12px;
        color: #666;
      }
    }
  }

  .dialog-footer {
    margin-top: 16px;

    .van-button {
      background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
      border: none;
    }
  }
}

// 骨架屏样式
.wish-list-inner {
  min-height: 200px;
}

.skeleton-item {
  pointer-events: none;

  .wish-header {
    display: flex;
    align-items: flex-start;

    .skeleton-icon {
      width: 24px;
      height: 24px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-right: 12px;
    }

    .wish-info {
      flex: 1;

      .skeleton-title {
        width: 60%;
        height: 15px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 4px;
        margin-bottom: 8px;
      }

      .skeleton-desc {
        width: 40%;
        height: 12px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 4px;
      }
    }
  }

  .wish-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #f5f5f5;

    .skeleton-time {
      width: 80px;
      height: 12px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
    }

    .skeleton-actions {
      width: 100px;
      height: 24px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
    }
  }
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
