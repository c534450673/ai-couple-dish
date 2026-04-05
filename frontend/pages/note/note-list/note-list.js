/**
 * 笔记列表页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    notes: [],
    loading: true
  },

  onLoad() {
    this.loadNotes();
  },

  onShow() {
    this.loadNotes();
  },

  loadNotes() {
    api.getNoteList().then(res => {
      this.setData({
        notes: res.data || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
    });
  },

  // 添加笔记
  onAddNote() {
    wx.navigateTo({
      url: '/pages/note/note-add/note-add'
    });
  },

  // 查看笔记详情
  onViewNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/note/note-detail/note-detail?id=${id}`
    });
  },

  // 删除笔记
  onDeleteNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这篇笔记吗？',
      success: (res) => {
        if (res.confirm) {
          api.deleteNote(id).then(() => {
            app.showSuccess('删除成功');
            this.loadNotes();
          });
        }
      }
    });
  }
});