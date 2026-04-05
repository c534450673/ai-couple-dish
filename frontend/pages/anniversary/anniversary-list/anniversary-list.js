/**
 * 纪念日列表页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    anniversaries: [],
    loading: true
  },

  onLoad() {
    this.loadAnniversaries();
  },

  onShow() {
    this.loadAnniversaries();
  },

  loadAnniversaries() {
    api.getAnniversaryList().then(res => {
      this.setData({
        anniversaries: res.data || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
    });
  },

  onAddAnniversary() {
    wx.navigateTo({
      url: '/pages/anniversary/anniversary-add/anniversary-add'
    });
  },

  onDeleteAnniversary(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个纪念日吗？',
      success: (res) => {
        if (res.confirm) {
          api.deleteAnniversary(id).then(() => {
            app.showSuccess('删除成功');
            this.loadAnniversaries();
          });
        }
      }
    });
  }
});