/**
 * 恋爱计时页面
 */
const app = getApp();
const api = require('../../services/api.js');

Page({
  data: {
    loveDays: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
    nextAnniversary: null,
    timer: null
  },

  onLoad() {
    this.loadTimer();
  },

  onUnload() {
    if (this.data.timer) {
      clearInterval(this.data.timer);
      this.setData({ timer: null });
    }
  },

  loadTimer() {
    api.getLoveTimer().then(res => {
      const data = res.data || {};
      this.setData({
        loveDays: data.days || 0,
        nextAnniversary: data.nextAnniversary
      });
      this.startTimer();
    });
  },

  startTimer() {
    // 实时更新时分秒
    const updateTime = () => {
      const now = new Date();
      const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
      const diff = endOfDay - now;

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      this.setData({
        hours: hours.toString().padStart(2, '0'),
        minutes: minutes.toString().padStart(2, '0'),
        seconds: seconds.toString().padStart(2, '0')
      });
    };

    updateTime();
    this.data.timer = setInterval(updateTime, 1000);
  },

  goToAnniversary() {
    wx.navigateTo({
      url: '/pages/anniversary/anniversary-list/anniversary-list'
    });
  }
});