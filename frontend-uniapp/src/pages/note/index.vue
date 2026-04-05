<template>
  <view class="note-page">
    <view class="nav-bar">
      <text class="title">美食笔记</text>
    </view>
    <view class="note-list" v-if="notes.length > 0">
      <view class="note-item" v-for="note in notes" :key="note.id" @click="goToDetail(note.id)">
        <image v-if="note.imageUrls && note.imageUrls.length > 0" :src="note.imageUrls[0]" class="note-image" mode="aspectFill" />
        <view class="note-content">
          <text class="note-title">{{ note.title }}</text>
          <text class="note-desc">{{ note.content }}</text>
          <text class="note-date">{{ note.createTime }}</text>
        </view>
      </view>
    </view>
    <view class="empty-state" v-else>
      <text class="empty-icon">📝</text>
      <text class="empty-text">还没有笔记</text>
      <text class="empty-subtext">记录你们的美食故事</text>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { noteApi } from '@/api'

const notes = ref([])

const loadNotes = async () => {
  try {
    const res = await noteApi.getNoteList()
    notes.value = res.data || []
  } catch (error) {
    console.error('加载笔记失败', error)
  }
}

const goToDetail = (id) => {
  uni.navigateTo({ url: `/pages/note/detail?id=${id}` })
}

onMounted(() => {
  loadNotes()
})
</script>

<style lang="scss" scoped>
.note-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.nav-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx 24rpx;
  background: #fff;

  .title {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
  }
}

.note-list {
  padding: 24rpx;
}

.note-item {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;

  .note-image {
    width: 160rpx;
    height: 160rpx;
    border-radius: 12rpx;
    margin-right: 24rpx;
  }

  .note-content {
    flex: 1;
    display: flex;
    flex-direction: column;

    .note-title {
      font-size: 30rpx;
      font-weight: 600;
      color: #333;
      margin-bottom: 12rpx;
    }

    .note-desc {
      font-size: 26rpx;
      color: #666;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .note-date {
      font-size: 24rpx;
      color: #999;
      margin-top: auto;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 200rpx;

  .empty-icon {
    font-size: 120rpx;
    margin-bottom: 24rpx;
  }

  .empty-text {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 12rpx;
  }

  .empty-subtext {
    font-size: 28rpx;
    color: #999;
  }
}
</style>