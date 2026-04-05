/**
 * 心愿单页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    wishes: [],
    loading: true
  },

  onLoad() {
    this.loadWishes();
  },

  onShow() {
    this.loadWishes();
  },

  loadWishes() {
    api.getWishList().then(res => {
      this.setData({
        wishes: res.data || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
    });
  },

  // 标记心愿为已实现
  onFulfill(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认',
      content: '确定要标记这个心愿为已实现吗？',
      success: (res) => {
        if (res.confirm) {
          api.fulfillWish(id).then(() => {
            app.showSuccess('已实现');
            this.loadWishes();
          });
        }
      }
    });
  },

  // 删除心愿
  onDelete(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个心愿吗？',
      success: (res) => {
        if (res.confirm) {
          api.deleteWish(id).then(() => {
            app.showSuccess('删除成功');
            this.loadWishes();
          });
        }
      }
    });
  }
});