/**
 * 情侣绑定页面
 */
const app = getApp();
const api = require('../../services/api.js');

Page({
  data: {
    mode: 'select', // select-选择模式, generate-生成码, input-输入码
    coupleCode: '',
    inputCode: '',
    loveStartDate: '',
    generating: false,
    binding: false,
    today: ''
  },

  onLoad() {
    // 演示模式下跳过绑定页
    if (app.globalData.isDemoMode) {
      wx.switchTab({
        url: '/pages/couple-home/couple-home'
      });
      return;
    }

    const today = new Date();
    this.setData({
      today: today.toISOString().split('T')[0]
    });
  },

  // 选择模式
  onSelectMode(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({ mode });
  },

  // 生成情侣码
  onGenerateCode() {
    if (!this.data.loveStartDate) {
      wx.showToast({
        title: '请选择恋爱开始日期',
        icon: 'none'
      });
      return;
    }

    this.setData({ generating: true });

    api.generateCoupleCode({
      loveStartDate: this.data.loveStartDate
    }).then(res => {
      this.setData({
        generating: false,
        coupleCode: res.data.coupleCode || res.data
      });
      wx.showToast({
        title: '情侣码已生成',
        icon: 'success'
      });
    }).catch(err => {
      this.setData({ generating: false });
    });
  },

  // 输入情侣码
  onInputCode(e) {
    this.setData({
      inputCode: e.detail.value.toUpperCase()
    });
  },

  // 绑定情侣
  onBindCouple() {
    if (!this.data.inputCode) {
      wx.showToast({
        title: '请输入情侣码',
        icon: 'none'
      });
      return;
    }

    if (this.data.inputCode.length !== 8) {
      wx.showToast({
        title: '情侣码为8位',
        icon: 'none'
      });
      return;
    }

    this.setData({ binding: true });

    api.bindCouple({
      coupleCode: this.data.inputCode
    }).then(res => {
      this.setData({ binding: false });
      app.showSuccess('绑定成功');

      // 更新全局情侣信息
      app.globalData.coupleInfo = res.data;

      // 跳转到首页
      setTimeout(() => {
        wx.switchTab({
          url: '/pages/couple-home/couple-home'
        });
      }, 1500);
    }).catch(err => {
      this.setData({ binding: false });
    });
  },

  // 复制情侣码
  onCopyCode() {
    wx.setClipboardData({
      data: this.data.coupleCode,
      success: () => {
        wx.showToast({
          title: '已复制',
          icon: 'success'
        });
      }
    });
  },

  // 分享情侣码
  onShareCode() {
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    });
  },

  // 日期选择
  onDateChange(e) {
    this.setData({
      loveStartDate: e.detail.value
    });
  },

  // 选择日期
  chooseDate() {
    const that = this;
    wx.showModal({
      title: '选择日期',
      editable: true,
      placeholderText: '格式：2024-01-01',
      success(res) {
        if (res.confirm && res.content) {
          const date = res.content;
          // 验证日期格式
          if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
            wx.showToast({
              title: '日期格式错误',
              icon: 'none'
            });
            return;
          }

          // 验证日期有效性
          const dateObj = new Date(date);
          if (isNaN(dateObj.getTime())) {
            wx.showToast({
              title: '日期无效',
              icon: 'none'
            });
            return;
          }

          // 验证不能是未来日期
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          if (dateObj > today) {
            wx.showToast({
              title: '不能选择未来日期',
              icon: 'none'
            });
            return;
          }

          that.setData({ loveStartDate: date });
        }
      }
    });
  }
});