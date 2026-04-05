/**
 * 情侣首页
 */
const app = getApp();
const api = require('../../services/api.js');

Page({
  data: {
    userInfo: null,
    coupleInfo: null,
    homeData: null,
    loading: true
  },

  onLoad() {
    this.setData({
      userInfo: app.globalData.userInfo,
      coupleInfo: app.globalData.coupleInfo
    });
  },

  onShow() {
    this.loadHomeData();
  },

  onPullDownRefresh() {
    this.loadHomeData().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 加载首页数据
  loadHomeData() {
    this.setData({ loading: true });

    return api.getCoupleHome().then(res => {
      this.setData({
        loading: false,
        homeData: res.data
      });
    }).catch(err => {
      this.setData({ loading: false });
      console.error('加载首页数据失败', err);
      wx.showModal({
        title: '加载失败',
        content: '数据加载失败，是否重试？',
        success: (res) => {
          if (res.confirm) {
            this.loadHomeData();
          }
        }
      });
    });
  },

  // 跳转到恋爱计时
  goToLoveTimer() {
    wx.navigateTo({
      url: '/pages/love-timer/love-timer'
    });
  },

  // 跳转到菜单
  goToMenu() {
    wx.switchTab({
      url: '/pages/menu/menu-list/menu-list'
    });
  },

  // 跳转到纪念日
  goToAnniversary() {
    wx.navigateTo({
      url: '/pages/anniversary/anniversary-list/anniversary-list'
    });
  },

  // 跳转到投喂
  goToFeed() {
    wx.switchTab({
      url: '/pages/feed/feed-home/feed-home'
    });
  },

  // 跳转到笔记
  goToNote() {
    wx.navigateTo({
      url: '/pages/note/note-list/note-list'
    });
  },

  // 跳转到相册
  goToPhoto() {
    wx.navigateTo({
      url: '/pages/photo/photo-list/photo-list'
    });
  },

  // 跳转到我的
  goToMy() {
    wx.switchTab({
      url: '/pages/my/my-home/my-home'
    });
  },

  // 解绑操作
  onUnbind() {
    wx.showModal({
      title: '确认解绑',
      content: '确定要解除情侣关系吗？解绑后数据将保留，但需要重新绑定。',
      success: (res) => {
        if (res.confirm) {
          api.applyUnbind({}).then(() => {
            app.showSuccess('已提交解绑申请');
            app.globalData.coupleInfo = null;
            setTimeout(() => {
              wx.redirectTo({
                url: '/pages/couple-bind/couple-bind'
              });
            }, 1500);
          });
        }
      }
    });
  }
});