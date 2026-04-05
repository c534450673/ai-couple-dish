/**
 * 订单列表页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    orders: [],
    loading: true,
    currentTab: 'all'
  },

  onLoad() {
    this.loadOrders();
  },

  onShow() {
    this.loadOrders();
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab });
    this.loadOrders();
  },

  loadOrders() {
    api.getChefOrderList({ status: this.data.currentTab }).then(res => {
      this.setData({
        orders: res.data || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    });
  },

  onProcessOrder(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认接单',
      content: '确定要接受这个订单吗？',
      success: (res) => {
        if (res.confirm) {
          api.processChefOrder(id).then(() => {
            app.showSuccess('接单成功');
            this.loadOrders();
          });
        }
      }
    });
  },

  onCompleteOrder(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认完成',
      content: '确定已完成这个订单吗？',
      success: (res) => {
        if (res.confirm) {
          api.completeChefOrder(id).then(() => {
            app.showSuccess('完成订单');
            this.loadOrders();
          });
        }
      }
    });
  }
});