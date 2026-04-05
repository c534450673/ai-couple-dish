/**
 * 照片上传页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    photos: [],
    loading: false
  },

  onChoosePhoto() {
    if (this.data.photos.length >= 9) {
      wx.showToast({ title: '最多上传9张', icon: 'none' });
      return;
    }

    wx.chooseImage({
      count: 9 - this.data.photos.length,
      success: (res) => {
        this.setData({
          photos: [...this.data.photos, ...res.tempFilePaths]
        });
      }
    });
  },

  onRemovePhoto(e) {
    const index = e.currentTarget.dataset.index;
    const photos = [...this.data.photos];
    photos.splice(index, 1);
    this.setData({ photos });
  },

  onUpload() {
    if (this.data.photos.length === 0) {
      wx.showToast({ title: '请选择照片', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    // 如果是演示模式，直接使用本地路径
    if (app.globalData.isDemoMode) {
      const urls = this.data.photos;
      api.uploadPhotos({ urls }).then(() => {
        this.setData({ loading: false, photos: [] });
        app.showSuccess('上传成功');
        setTimeout(() => wx.navigateBack(), 1500);
      }).catch(() => {
        this.setData({ loading: false });
      });
      return;
    }

    // 真实上传：逐个上传照片
    const uploadPromises = this.data.photos.map(filePath => {
      return new Promise((resolve, reject) => {
        wx.uploadFile({
          url: app.globalData.baseUrl + '/upload/image',
          filePath: filePath,
          name: 'file',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : ''
          },
          success: (res) => {
            try {
              const data = JSON.parse(res.data);
              if (data.code === 200) {
                resolve(data.data.url);
              } else {
                reject(data.message || '上传失败');
              }
            } catch (e) {
              reject('上传失败');
            }
          },
          fail: (err) => {
            reject(err);
          }
        });
      });
    });

    // 等待所有照片上传完成
    Promise.all(uploadPromises).then(urls => {
      // 调用API保存照片记录
      return api.uploadPhotos({ urls });
    }).then(() => {
      this.setData({ loading: false, photos: [] });
      app.showSuccess('上传成功');
      setTimeout(() => wx.navigateBack(), 1500);
    }).catch((err) => {
      this.setData({ loading: false });
      wx.showToast({
        title: typeof err === 'string' ? err : '上传失败',
        icon: 'none'
      });
    });
  }
});