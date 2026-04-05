/**
 * 我的页面
 */
const app = getApp();
const api = require('../../services/api.js');

Page({
  data: {
    userInfo: null,
    coupleInfo: null,
    menuCount: 0,
    noteCount: 0,
    feedCount: 0
  },

  onLoad() {
    this.setData({
      userInfo: app.globalData.userInfo,
      coupleInfo: app.globalData.coupleInfo,
      isDemoMode: app.globalData.isDemoMode
    });
  },

  onShow() {
    this.loadStats();
  },

  loadStats() {
    api.getMenuStats().then(res => {
      this.setData({
        menuCount: (res.data.wantToGoCount || 0) + (res.data.beenToCount || 0) + (res.data.recommendedCount || 0)
      });
    });

    api.getNoteList().then(res => {
      this.setData({
        noteCount: res.data ? res.data.length : 0
      });
    });
  },

  // 跳转到设置
  goToSettings() {
    wx.navigateTo({
      url: '/pages/my/settings/settings'
    });
  },

  // 跳转到笔记
  goToNotes() {
    wx.navigateTo({
      url: '/pages/note/note-list/note-list'
    });
  },

  // 跳转到纪念日
  goToAnniversary() {
    wx.navigateTo({
      url: '/pages/anniversary/anniversary-list/anniversary-list'
    });
  },

  // 跳转到相册
  goToPhoto() {
    wx.navigateTo({
      url: '/pages/photo/photo-list/photo-list'
    });
  },

  // 跳转到心愿单
  goToWish() {
    wx.navigateTo({
      url: '/pages/feed/wish-list/wish-list'
    });
  },

  // 退出登录
  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.logout();
          wx.redirectTo({
            url: '/pages/index/index'
          });
        }
      }
    });
  }
});