/**
 * 添加笔记页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    title: '',
    content: '',
    images: [],
    loading: false
  },

  onTitleInput(e) {
    this.setData({ title: e.detail.value });
  },

  onContentInput(e) {
    this.setData({ content: e.detail.value });
  },

  onChooseImage() {
    if (this.data.images.length >= 9) {
      wx.showToast({ title: '最多上传9张图片', icon: 'none' });
      return;
    }

    wx.chooseImage({
      count: 9 - this.data.images.length,
      success: (res) => {
        this.setData({
          images: [...this.data.images, ...res.tempFilePaths]
        });
      }
    });
  },

  onRemoveImage(e) {
    const index = e.currentTarget.dataset.index;
    const images = [...this.data.images];
    images.splice(index, 1);
    this.setData({ images });
  },

  onSave() {
    if (!this.data.title) {
      wx.showToast({ title: '请输入标题', icon: 'none' });
      return;
    }

    if (!this.data.content) {
      wx.showToast({ title: '请输入内容', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    // 如果有图片，先上传图片
    if (this.data.images.length > 0 && !app.globalData.isDemoMode) {
      this.uploadImages()
        .then(imageUrls => this.saveNote(imageUrls))
        .catch(() => {
          this.setData({ loading: false });
        });
    } else {
      // 没有图片或演示模式，直接保存
      this.saveNote(this.data.images);
    }
  },

  // 上传图片
  uploadImages() {
    return new Promise((resolve, reject) => {
      const uploadPromises = this.data.images.map(filePath => {
        return new Promise((res, rej) => {
          wx.uploadFile({
            url: app.globalData.baseUrl + '/upload/image',
            filePath: filePath,
            name: 'file',
            header: {
              'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : ''
            },
            success: (uploadRes) => {
              try {
                const data = JSON.parse(uploadRes.data);
                if (data.code === 200) {
                  res(data.data.url);
                } else {
                  rej(data.message || '上传失败');
                }
              } catch (e) {
                rej('上传失败');
              }
            },
            fail: (err) => {
              rej(err);
            }
          });
        });
      });

      Promise.all(uploadPromises).then(urls => {
        resolve(urls);
      }).catch(err => {
        wx.showToast({
          title: typeof err === 'string' ? err : '图片上传失败',
          icon: 'none'
        });
        reject(err);
      });
    });
  },

  // 保存笔记
  saveNote(imageUrls) {
    return api.addNote({
      title: this.data.title,
      content: this.data.content,
      images: imageUrls
    }).then(() => {
      app.showSuccess('添加成功');
      setTimeout(() => wx.navigateBack(), 1500);
    }).catch(() => {
      this.setData({ loading: false });
    });
  }
});