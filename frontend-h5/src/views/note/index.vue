<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { noteApi } from '@/api'
import AppTabbar from '@/components/AppTabbar.vue'

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

<template>
  <div class="note-page">
    <header class="page-topbar">
      <span class="placeholder" />
      <h1 class="page-title">
        美食笔记
      </h1>
      <button
        class="add"
        @click="$router.push('/note/add')"
      >
        <van-icon
          name="plus"
          size="20"
        />
      </button>
    </header>

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
        title="美食记录"
        name="0"
      />
      <van-tab
        title="心情随笔"
        name="1"
      />
      <van-tab
        title="约会日记"
        name="2"
      />
    </van-tabs>

    <div class="note-body">
      <div
        v-for="item in noteList"
        :key="item.id"
        class="note-card"
        @click="$router.push(`/note/${item.id}`)"
      >
        <div class="note-head">
          <img
            v-if="item.authorAvatar"
            :src="item.authorAvatar"
            class="author-avatar"
          >
          <span
            v-else
            class="author-avatar fallback"
          ><van-icon name="user-o" /></span>
          <div class="author-info">
            <div class="author-name">
              {{ item.authorName }}
            </div>
            <div class="note-time">
              {{ item.createTime }}
            </div>
          </div>
          <van-tag
            round
            type="primary"
            plain
          >
            {{ getNoteTypeText(item.noteType) }}
          </van-tag>
        </div>
        <div class="note-title">
          {{ item.title }}
        </div>
        <div class="note-content">
          {{ item.content }}
        </div>
        <div
          v-if="item.coverPhotoUrl"
          class="note-cover"
        >
          <img
            v-lazy="item.coverPhotoUrl"
            alt="cover"
          >
        </div>
        <div class="note-foot">
          <span><van-icon name="eye-o" /> {{ item.viewCount || 0 }}</span>
          <span><van-icon name="like-o" /> {{ item.likeCount || 0 }}</span>
          <span><van-icon name="comment-o" /> {{ item.commentCount || 0 }}</span>
        </div>
      </div>

      <van-empty
        v-if="noteList.length === 0"
        description="暂无笔记"
      >
        <van-button
          type="primary"
          round
          @click="$router.push('/note/add')"
        >
          写笔记
        </van-button>
      </van-empty>
    </div>

    <app-tabbar />
  </div>
</template>

<style lang="scss" scoped>
.note-page {
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

.note-body { padding: $space-4 $page-padding 0; }

.note-card {
  @include card($radius-lg, $space-4);
  margin-bottom: $space-4;
  transition: transform $transition-base;
  &:active { transform: scale(0.99); }

  .note-head {
    display: flex;
    align-items: center;
    gap: $space-3;
    margin-bottom: $space-3;

    .author-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      object-fit: cover;

      &.fallback {
        display: flex;
        align-items: center;
        justify-content: center;
        background: $color-surface-high;
        color: $color-on-surface-variant;
      }
    }

    .author-info {
      flex: 1;
      .author-name { font-size: $fs-label; font-weight: $fw-medium; color: $color-on-surface; }
      .note-time { font-size: $fs-caption; color: $color-on-surface-variant; }
    }
  }

  .note-title {
    font-size: $fs-title;
    font-weight: $fw-semibold;
    color: $color-on-surface;
    margin-bottom: $space-2;
  }

  .note-content {
    font-size: $fs-label;
    color: $color-on-surface-variant;
    line-height: 1.6;
    @include ellipsis-lines(2);
  }

  .note-cover {
    margin-top: $space-3;
    img { width: 100%; height: 160px; border-radius: $radius-md; object-fit: cover; }
  }

  .note-foot {
    display: flex;
    gap: $space-5;
    margin-top: $space-3;
    color: $color-on-surface-variant;
    font-size: $fs-caption;

    span { display: flex; align-items: center; gap: 4px; }
  }
}
</style>
