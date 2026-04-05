/**
 * 添加纪念日页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    name: '',
    date: '',
    loading: false
  },

  onNameInput(e) {
    this.setData({ name: e.detail.value });
  },

  onDateChange(e) {
    this.setData({ date: e.detail.value });
  },

  onSave() {
    if (!this.data.name) {
      wx.showToast({ title: '请输入纪念日名称', icon: 'none' });
      return;
    }

    if (!this.data.date) {
      wx.showToast({ title: '请选择日期', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    api.addAnniversary({
      name: this.data.name,
      date: this.data.date
    }).then(() => {
      app.showSuccess('添加成功');
      setTimeout(() => wx.navigateBack(), 1500);
    }).catch(() => {
      this.setData({ loading: false });
    });
  }
});