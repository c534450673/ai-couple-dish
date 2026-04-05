/**
 * 发送投喂页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    feedType: 'meal',
    content: '',
    message: '',
    images: [],
    sending: false
  },

  // 选择投喂类型
  onSelectType(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ feedType: type });
  },

  // 输入内容
  onContentInput(e) {
    this.setData({
      content: e.detail.value
    });
  },

  // 输入留言
  onMessageInput(e) {
    this.setData({
      message: e.detail.value
    });
  },

  // 选择图片
  onChooseImage() {
    if (this.data.images.length >= 3) {
      wx.showToast({
        title: '最多上传3张图片',
        icon: 'none'
      });
      return;
    }

    wx.chooseImage({
      count: 3 - this.data.images.length,
      success: (res) => {
        this.setData({
          images: [...this.data.images, ...res.tempFilePaths]
        });
      }
    });
  },

  // 删除图片
  onRemoveImage(e) {
    const index = e.currentTarget.dataset.index;
    const images = [...this.data.images];
    images.splice(index, 1);
    this.setData({ images });
  },

  // 发送投喂
  onSend() {
    if (!this.data.content) {
      wx.showToast({
        title: '请输入投喂内容',
        icon: 'none'
      });
      return;
    }

    this.setData({ sending: true });

    // 如果有图片，先上传图片
    if (this.data.images.length > 0 && !app.globalData.isDemoMode) {
      this.uploadImages()
        .then(imageUrls => this.sendFeedRequest(imageUrls))
        .catch(() => {
          this.setData({ sending: false });
        });
    } else {
      // 没有图片或演示模式，直接发送
      this.sendFeedRequest(this.data.images);
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

  // 发送投喂请求
  sendFeedRequest(imageUrls) {
    return api.sendFeed({
      feedType: this.data.feedType,
      content: this.data.content,
      message: this.data.message,
      imageUrls: imageUrls
    }).then(() => {
      this.setData({ sending: false });
      app.showSuccess('投喂发送成功');
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    }).catch(err => {
      this.setData({ sending: false });
    });
  }
});