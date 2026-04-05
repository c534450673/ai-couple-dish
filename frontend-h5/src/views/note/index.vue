<template>
  <div class="note-page">
    <van-nav-bar title="美食笔记">
      <template #right>
        <van-icon name="plus" size="20" @click="$router.push('/note/add')" />
      </template>
    </van-nav-bar>

    <van-tabs v-model:active="activeTab" sticky @change="onTabChange">
      <van-tab title="全部" name="all"></van-tab>
      <van-tab title="美食记录" name="0"></van-tab>
      <van-tab title="心情随笔" name="1"></van-tab>
      <van-tab title="约会日记" name="2"></van-tab>
    </van-tabs>

    <div class="note-list">
      <div v-for="item in noteList" :key="item.id" class="note-item card" @click="$router.push(`/note/${item.id}`)">
        <div class="note-header">
          <img v-if="item.authorAvatar" :src="item.authorAvatar" class="author-avatar" />
          <div class="author-info">
            <div class="author-name">{{ item.authorName }}</div>
            <div class="note-time">{{ item.createTime }}</div>
          </div>
          <van-tag size="small">{{ getNoteTypeText(item.noteType) }}</van-tag>
        </div>
        <div class="note-title">{{ item.title }}</div>
        <div class="note-content">{{ item.content }}</div>
        <div class="note-images" v-if="item.coverPhotoUrl">
          <img :src="item.coverPhotoUrl" />
        </div>
        <div class="note-footer">
          <span><van-icon name="eye-o" /> {{ item.viewCount || 0 }}</span>
          <span><van-icon name="like-o" /> {{ item.likeCount || 0 }}</span>
          <span><van-icon name="comment-o" /> {{ item.commentCount || 0 }}</span>
        </div>
      </div>

      <van-empty v-if="noteList.length === 0" description="暂无笔记">
        <van-button type="primary" round @click="$router.push('/note/add')">写笔记</van-button>
      </van-empty>
    </div>

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
import { showToast, showLoadingToast, closeToast } from 'vant'
import { noteApi } from '@/api'

const activeTab = ref('all')
const noteList = ref([])

const getNoteTypeText = (type) => {
  const map = { 0: '美食记录', 1: '心情随笔', 2: '约会日记' }
  return map[type] || '美食记录'
}

const loadNoteList = async () => {
  showLoadingToast({ message: '加载中...', forbidClick: true })
  try {
    const params = activeTab.value !== 'all' ? { noteType: activeTab.value } : {}
    const res = await noteApi.getNoteList(params)
    noteList.value = res.data?.list || []
  } catch (error) {
    showToast('加载失败')
  } finally {
    closeToast()
  }
}

const onTabChange = () => {
  loadNoteList()
}

onMounted(() => {
  loadNoteList()
})
</script>

<style lang="scss" scoped>
.note-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 70px;
}

.note-list {
  padding: 12px 16px;

  .note-item {
    padding: 16px;
    margin-bottom: 12px;

    .note-header {
      display: flex;
      align-items: center;
      margin-bottom: 12px;

      .author-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        margin-right: 10px;
      }

      .author-info {
        flex: 1;

        .author-name {
          font-size: 14px;
          font-weight: 500;
          color: #333;
        }

        .note-time {
          font-size: 12px;
          color: #999;
        }
      }
    }

    .note-title {
      font-size: 16px;
      font-weight: 600;
      color: #333;
      margin-bottom: 8px;
    }

    .note-content {
      font-size: 14px;
      color: #666;
      line-height: 1.5;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    .note-images {
      margin-top: 12px;

      img {
        width: 120px;
        height: 120px;
        border-radius: 8px;
        object-fit: cover;
      }
    }

    .note-footer {
      display: flex;
      gap: 20px;
      margin-top: 12px;
      color: #999;
      font-size: 12px;

      span {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }
}
</style>
