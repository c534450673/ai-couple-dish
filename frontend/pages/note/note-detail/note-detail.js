/**
 * 笔记详情页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    noteId: null,
    noteInfo: null,
    loading: true
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ noteId: options.id });
      this.loadNoteDetail(options.id);
    }
  },

  loadNoteDetail(id) {
    api.getNoteDetail(id).then(res => {
      this.setData({
        noteInfo: res.data,
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  onDelete() {
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这篇笔记吗？',
      success: (res) => {
        if (res.confirm) {
          api.deleteNote(this.data.noteId).then(() => {
            app.showSuccess('删除成功');
            setTimeout(() => wx.navigateBack(), 1500);
          });
        }
      }
    });
  }
});