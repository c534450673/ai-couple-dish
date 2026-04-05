/**
 * 情侣私密菜单 - 应用入口
 */
App({
  globalData: {
    userInfo: null,
    token: null,
    coupleInfo: null,
    isLoggedIn: false,
    isDemoMode: false,
    baseUrl: 'http://localhost:8080/api'
  },

  onLaunch() {
    // 检查登录状态
    this.checkLoginStatus();

    // 监听网络状态变化
    this.setupNetworkListener();
  },

  // 设置网络监听
  setupNetworkListener() {
    // 监听网络状态变化
    wx.onNetworkStatusChange((res) => {
      if (!res.isConnected) {
        wx.showToast({
          title: '网络已断开',
          icon: 'none',
          duration: 2000
        });
      } else {
        wx.showToast({
          title: '网络已连接',
          icon: 'success',
          duration: 1500
        });
      }
    });

    // 检查当前网络状态
    wx.getNetworkType({
      success: (res) => {
        if (res.networkType === 'none') {
          wx.showModal({
            title: '网络提示',
            content: '当前无网络连接，部分功能可能无法使用',
            showCancel: false
          });
        }
      }
    });
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    const isDemoMode = wx.getStorageSync('isDemoMode');

    if (isDemoMode) {
      // 恢复演示模式
      this.globalData.isDemoMode = true;
      this.globalData.isLoggedIn = true;
      this.globalData.userInfo = wx.getStorageSync('demoUserInfo') || this.getDemoUserInfo();
      this.globalData.coupleInfo = wx.getStorageSync('demoCoupleInfo') || this.getDemoCoupleInfo();
      return;
    }

    if (token && userInfo) {
      this.globalData.token = token;
      this.globalData.userInfo = userInfo;
      this.globalData.isLoggedIn = true;

      // 获取情侣信息
      this.getCoupleInfo();
    }
  },

  // 获取演示用户信息
  getDemoUserInfo() {
    return {
      id: 'demo_user_1',
      nickName: '演示用户',
      avatarUrl: '/assets/images/default-avatar.png',
      coupleCode: 'DEMO1234'
    };
  },

  // 获取演示情侣信息
  getDemoCoupleInfo() {
    return {
      id: 'demo_couple_1',
      coupleCode: 'DEMO5678',
      partnerName: 'TA',
      partnerAvatar: '/assets/images/default-avatar.png',
      startDate: '2024-01-01',
      loveDays: 444
    };
  },

  // 设置演示模式
  setDemoMode() {
    const demoUser = this.getDemoUserInfo();
    const demoCouple = this.getDemoCoupleInfo();

    this.globalData.isDemoMode = true;
    this.globalData.isLoggedIn = true;
    this.globalData.userInfo = demoUser;
    this.globalData.coupleInfo = demoCouple;

    wx.setStorageSync('isDemoMode', true);
    wx.setStorageSync('demoUserInfo', demoUser);
    wx.setStorageSync('demoCoupleInfo', demoCouple);
  },

  // 退出演示模式
  exitDemoMode() {
    this.globalData.isDemoMode = false;
    this.globalData.isLoggedIn = false;
    this.globalData.userInfo = null;
    this.globalData.coupleInfo = null;

    wx.removeStorageSync('isDemoMode');
    wx.removeStorageSync('demoUserInfo');
    wx.removeStorageSync('demoCoupleInfo');
    wx.removeStorageSync('demoData');  // 清除演示数据
  },

  // 设置登录信息
  setLoginInfo(token, userInfo) {
    this.globalData.token = token;
    this.globalData.userInfo = userInfo;
    this.globalData.isLoggedIn = true;

    wx.setStorageSync('token', token);
    wx.setStorageSync('userInfo', userInfo);

    // 获取情侣信息
    this.getCoupleInfo();
  },

  // 获取情侣信息
  getCoupleInfo() {
    if (!this.globalData.token) return;

    this.request({
      url: '/couple/info',
      method: 'GET'
    }).then(res => {
      if (res.code === 200) {
        this.globalData.coupleInfo = res.data;
      }
    }).catch(() => {
      // 未绑定情侣关系
      this.globalData.coupleInfo = null;
    });
  },

  // 登出
  logout() {
    // 如果是演示模式，清除演示状态
    if (this.globalData.isDemoMode) {
      this.exitDemoMode();
      return;
    }

    this.globalData.token = null;
    this.globalData.userInfo = null;
    this.globalData.coupleInfo = null;
    this.globalData.isLoggedIn = false;

    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
  },

  // 通用请求方法
  request(options) {
    const {
      url,
      method = 'GET',
      data = {},
      header = {}
    } = options;

    return new Promise((resolve, reject) => {
      // 先检查网络状态
      wx.getNetworkType({
        success: (netRes) => {
          if (netRes.networkType === 'none') {
            wx.showToast({
              title: '网络未连接',
              icon: 'none'
            });
            reject({ code: -1, message: '网络未连接' });
            return;
          }

          wx.showLoading({
            title: '加载中...',
            mask: true
          });

          wx.request({
            url: this.globalData.baseUrl + url,
            method,
            data,
            header: {
              'Content-Type': 'application/json',
              'Authorization': this.globalData.token ? `Bearer ${this.globalData.token}` : '',
              ...header
            },
            success: (res) => {
              wx.hideLoading();

              if (res.statusCode === 200) {
                if (res.data.code === 200) {
                  resolve(res.data);
                } else if (res.data.code === 401) {
                  // token过期，重新登录
                  this.logout();
                  wx.redirectTo({
                    url: '/pages/index/index'
                  });
                  reject(res.data);
                } else {
                  wx.showToast({
                    title: res.data.message || '请求失败',
                    icon: 'none'
                  });
                  reject(res.data);
                }
              } else {
                wx.showToast({
                  title: '网络错误',
                  icon: 'none'
                });
                reject(res);
              }
            },
            fail: (err) => {
              wx.hideLoading();
              wx.showToast({
                title: '网络错误',
                icon: 'none'
              });
              reject(err);
            }
          });
        },
        fail: () => {
          wx.showToast({
            title: '网络检测失败',
            icon: 'none'
          });
          reject({ code: -1, message: '网络检测失败' });
        }
      });
    });
  },

  // 显示成功提示
  showSuccess(title = '操作成功') {
    wx.showToast({
      title,
      icon: 'success',
      duration: 2000
    });
  },

  // 显示错误提示
  showError(title = '操作失败') {
    wx.showToast({
      title,
      icon: 'none',
      duration: 2000
    });
  }
});