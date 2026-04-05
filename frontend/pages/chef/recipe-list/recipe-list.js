/**
 * 食谱列表页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    recipes: [],
    loading: true
  },

  onLoad() {
    this.loadRecipes();
  },

  onShow() {
    this.loadRecipes();
  },

  loadRecipes() {
    api.getRecipeList().then(res => {
      this.setData({
        recipes: res.data || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    });
  }
});