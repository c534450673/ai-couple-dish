/**
 * 设置页面
 */
const app = getApp();

Page({
  data: {},

  onLoad() {
    this.setData({
      userInfo: app.globalData.userInfo
    });
  },

  // 切换情侣绑定状态
  onToggleCouple() {
    const coupleInfo = app.globalData.coupleInfo;
    if (coupleInfo) {
      wx.showModal({
        title: '解除绑定',
        content: '确定要解除与TA的绑定吗？',
        success: (res) => {
          if (res.confirm) {
            // 调用解绑API
            const api = require('../../services/api.js');
            api.applyUnbind({}).then(() => {
              app.showSuccess('已提交解绑申请');
              app.globalData.coupleInfo = null;
              setTimeout(() => {
                wx.redirectTo({ url: '/pages/couple-bind/couple-bind' });
              }, 1500);
            }).catch(() => {
              wx.showToast({
                title: '解绑失败，请重试',
                icon: 'none'
              });
            });
          }
        }
      });
    } else {
      wx.navigateTo({
        url: '/pages/couple-bind/couple-bind'
      });
    }
  },

  // 清除缓存
  onClearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '确定要清除本地缓存吗？不会清除登录信息。',
      success: (res) => {
        if (res.confirm) {
          // 保存关键信息
          const token = wx.getStorageSync('token');
          const userInfo = wx.getStorageSync('userInfo');
          const isDemoMode = wx.getStorageSync('isDemoMode');
          const demoUserInfo = wx.getStorageSync('demoUserInfo');
          const demoCoupleInfo = wx.getStorageSync('demoCoupleInfo');

          // 清除所有缓存
          wx.clearStorageSync();

          // 恢复关键信息
          if (token) wx.setStorageSync('token', token);
          if (userInfo) wx.setStorageSync('userInfo', userInfo);
          if (isDemoMode) {
            wx.setStorageSync('isDemoMode', isDemoMode);
            wx.setStorageSync('demoUserInfo', demoUserInfo);
            wx.setStorageSync('demoCoupleInfo', demoCoupleInfo);
          }

          app.showSuccess('缓存已清除');
        }
      }
    });
  },

  // 关于我们
  onAbout() {
    wx.showModal({
      title: '关于我们',
      content: '情侣私密菜单 V1.0\n让美食连接彼此',
      showCancel: false
    });
  }
});