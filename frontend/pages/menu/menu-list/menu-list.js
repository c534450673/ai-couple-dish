/**
 * 菜单列表页
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    tabs: [
      { key: '', name: '全部' },
      { key: 'wantToGo', name: '想去' },
      { key: 'beenTo', name: '去过' },
      { key: 'recommended', name: '种草' }
    ],
    currentTab: '',
    menuList: [],
    loading: false,
    empty: false
  },

  onLoad() {
    this.loadMenuList();
  },

  onShow() {
    this.loadMenuList();
  },

  onPullDownRefresh() {
    this.loadMenuList().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 切换Tab
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab });
    this.loadMenuList();
  },

  // 加载菜单列表
  loadMenuList() {
    this.setData({ loading: true });

    return api.getMenuList({ status: this.data.currentTab }).then(res => {
      this.setData({
        loading: false,
        menuList: res.data || [],
        empty: !res.data || res.data.length === 0
      });
    }).catch(err => {
      this.setData({
        loading: false,
        empty: true
      });
    });
  },

  // 跳转到菜单详情
  goToDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/menu/menu-detail/menu-detail?id=${id}`
    });
  },

  // 跳转到添加菜单
  goToAdd() {
    wx.navigateTo({
      url: '/pages/menu/menu-add/menu-add'
    });
  },

  // 点赞
  onLike(e) {
    const id = e.currentTarget.dataset.id;
    const index = e.currentTarget.dataset.index;
    const menu = this.data.menuList[index];

    api.likeMenu(id).then(() => {
      const list = this.data.menuList;
      // 切换点赞状态
      if (menu.isLiked) {
        list[index].likeCount = Math.max((menu.likeCount || 0) - 1, 0);
        list[index].isLiked = false;
      } else {
        list[index].likeCount = (menu.likeCount || 0) + 1;
        list[index].isLiked = true;
      }
      this.setData({ menuList: list });
    });
  },

  // 预览图片
  previewImage(e) {
    const url = e.currentTarget.dataset.url;
    wx.previewImage({
      current: url,
      urls: [url]
    });
  }
});