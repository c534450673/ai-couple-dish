/**
 * 相册列表页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    photos: [],
    loading: true
  },

  onLoad() {
    this.loadPhotos();
  },

  onShow() {
    this.loadPhotos();
  },

  loadPhotos() {
    api.getPhotoList().then(res => {
      this.setData({
        photos: res.data || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ loading: false });
    });
  },

  onUpload() {
    wx.navigateTo({
      url: '/pages/photo/photo-upload/photo-upload'
    });
  },

  onPreviewPhoto(e) {
    const url = e.currentTarget.dataset.url;
    if (!url) {
      wx.showToast({
        title: '图片地址无效',
        icon: 'none'
      });
      return;
    }

    const urls = this.data.photos
      .filter(p => p.url)
      .map(p => p.url);

    wx.previewImage({
      current: url,
      urls: urls
    });
  },

  onDeletePhoto(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这张照片吗？',
      success: (res) => {
        if (res.confirm) {
          api.deletePhoto(id).then(() => {
            app.showSuccess('删除成功');
            this.loadPhotos();
          });
        }
      }
    });
  }
});