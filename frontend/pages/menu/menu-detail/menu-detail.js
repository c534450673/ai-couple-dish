/**
 * 菜单详情页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    menuId: null,
    menuInfo: null,
    loading: true
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ menuId: options.id });
      this.loadMenuDetail(options.id);
    }
  },

  loadMenuDetail(id) {
    api.getMenuDetail(id).then(res => {
      this.setData({
        menuInfo: res.data,
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  // 编辑菜单
  onEdit() {
    wx.navigateTo({
      url: `/pages/menu/menu-add/menu-add?id=${this.data.menuId}`
    });
  },

  // 删除菜单
  onDelete() {
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个菜单吗？',
      success: (res) => {
        if (res.confirm) {
          api.deleteMenu(this.data.menuId).then(() => {
            app.showSuccess('删除成功');
            setTimeout(() => wx.navigateBack(), 1500);
          });
        }
      }
    });
  }
});