/**
 * 投喂首页
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    todayFeed: null,
    receivedList: [],
    sentList: [],
    loading: true
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.loadData();
  },

  onPullDownRefresh() {
    this.loadData().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  loadData() {
    this.setData({ loading: true });

    return Promise.all([
      api.getTodayFeedStatus(),
      api.getReceivedFeeds(),
      api.getSentFeeds()
    ]).then(results => {
      this.setData({
        loading: false,
        todayFeed: results[0].data,
        receivedList: results[1].data || [],
        sentList: results[2].data || []
      });
    }).catch(err => {
      this.setData({ loading: false });
    });
  },

  // 发送投喂
  goToSend() {
    if (this.data.todayFeed && this.data.todayFeed.sentToday) {
      wx.showToast({
        title: '今日已发送投喂',
        icon: 'none'
      });
      return;
    }
    wx.navigateTo({
      url: '/pages/feed/feed-send/feed-send'
    });
  },

  // 心愿单
  goToWishList() {
    wx.navigateTo({
      url: '/pages/feed/wish-list/wish-list'
    });
  },

  // 接受投喂
  onAccept(e) {
    const id = e.currentTarget.dataset.id;
    api.acceptFeed(id).then(() => {
      app.showSuccess('已接受投喂');
      this.loadData();
    });
  },

  // 拒绝投喂
  onReject(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '拒绝投喂',
      editable: true,
      placeholderText: '请输入拒绝原因（可选）',
      success: (res) => {
        if (res.confirm) {
          api.rejectFeed(id, res.content).then(() => {
            app.showSuccess('已拒绝');
            this.loadData();
          });
        }
      }
    });
  }
});