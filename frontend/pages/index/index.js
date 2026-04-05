/**
 * 首页/登录页
 */
const app = getApp();
const api = require('../../services/api.js');

Page({
  data: {
    hasUserInfo: false,
    userInfo: null,
    canIUse: wx.canIUse('button.open-type.getUserInfo')
  },

  onLoad() {
    // 检查是否已登录
    if (app.globalData.isLoggedIn) {
      this.goToHome();
    }
  },

  // 获取用户信息
  getUserProfile(e) {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        this.setData({
          userInfo: res.userInfo,
          hasUserInfo: true
        });

        // 调用微信登录
        this.wxLogin(res.userInfo);
      },
      fail: (err) => {
        console.error('获取用户信息失败', err);
        wx.showModal({
          title: '授权失败',
          content: '需要授权才能继续使用，是否重试？',
          success: (res) => {
            if (res.confirm) {
              // 用户点击确定，重新调用授权
              this.getUserProfile(e);
            }
          }
        });
      }
    });
  },

  // 微信登录
  wxLogin(userInfo) {
    wx.showLoading({
      title: '登录中...'
    });

    // 调用wx.login获取code
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          // 调用后端登录接口
          api.login({
            code: loginRes.code,
            nickName: userInfo.nickName,
            avatarUrl: userInfo.avatarUrl
          }).then(res => {
            wx.hideLoading();

            // 保存登录信息
            app.setLoginInfo(res.data.token, res.data.userInfo);

            // 跳转到首页
            this.goToHome();
          }).catch(err => {
            wx.hideLoading();
            console.error('登录接口调用失败', err);
            wx.showModal({
              title: '登录失败',
              content: '网络错误，是否重试？',
              success: (res) => {
                if (res.confirm) {
                  this.wxLogin(userInfo);
                }
              }
            });
          });
        } else {
          wx.hideLoading();
          console.error('wx.login失败', loginRes);
          wx.showModal({
            title: '登录失败',
            content: '获取登录凭证失败，是否重试？',
            success: (res) => {
              if (res.confirm) {
                this.wxLogin(userInfo);
              }
            }
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('wx.login调用失败', err);
        wx.showModal({
          title: '微信登录失败',
          content: '请检查网络连接后重试',
          success: (res) => {
            if (res.confirm) {
              this.wxLogin(userInfo);
            }
          }
        });
      }
    });
  },

  // 跳转到首页
  goToHome() {
    // 检查是否已绑定情侣
    if (app.globalData.coupleInfo) {
      wx.switchTab({
        url: '/pages/couple-home/couple-home'
      });
    } else {
      wx.redirectTo({
        url: '/pages/couple-bind/couple-bind'
      });
    }
  },

  // 游客模式（演示用）
  guestMode() {
    wx.showModal({
      title: '演示模式',
      content: '即将以游客身份体验所有功能，数据仅保存在本地。是否继续？',
      success: (res) => {
        if (res.confirm) {
          // 设置演示模式
          app.setDemoMode();

          // 跳转到首页
          wx.switchTab({
            url: '/pages/couple-home/couple-home'
          });
        }
      }
    });
  }
});