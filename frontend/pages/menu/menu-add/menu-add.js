/**
 * 添加/编辑菜单页面
 */
const app = getApp();
const api = require('../../../services/api.js');

Page({
  data: {
    menuId: null,
    isEdit: false,
    menuType: 'wantToGo',
    name: '',
    location: '',
    averageCost: '',
    recommendedDishes: '',
    notes: '',
    imageUrl: '',
    loading: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({
        menuId: options.id,
        isEdit: true
      });
      wx.setNavigationBarTitle({ title: '编辑菜单' });
      this.loadMenuDetail(options.id);
    }
  },

  loadMenuDetail(id) {
    api.getMenuDetail(id).then(res => {
      const menu = res.data;
      this.setData({
        menuType: menu.menuType || 'wantToGo',
        name: menu.name || '',
        location: menu.location || '',
        averageCost: menu.averageCost || '',
        recommendedDishes: menu.recommendedDishes || '',
        notes: menu.notes || '',
        imageUrl: menu.imageUrl || ''
      });
    }).catch(() => {
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    });
  },

  // 选择菜单类型
  onSelectType(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ menuType: type });
  },

  // 输入名称
  onNameInput(e) {
    this.setData({ name: e.detail.value });
  },

  // 输入位置
  onLocationInput(e) {
    this.setData({ location: e.detail.value });
  },

  // 输入人均
  onCostInput(e) {
    this.setData({ averageCost: e.detail.value });
  },

  // 输入推荐菜
  onDishesInput(e) {
    this.setData({ recommendedDishes: e.detail.value });
  },

  // 输入备注
  onNotesInput(e) {
    this.setData({ notes: e.detail.value });
  },

  // 选择图片
  onChooseImage() {
    wx.chooseImage({
      count: 1,
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0];

        // 显示上传中
        wx.showLoading({
          title: '上传中...',
          mask: true
        });

        // 上传图片到服务器
        wx.uploadFile({
          url: app.globalData.baseUrl + '/upload/image',
          filePath: tempFilePath,
          name: 'file',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : ''
          },
          success: (uploadRes) => {
            wx.hideLoading();
            try {
              const data = JSON.parse(uploadRes.data);
              if (data.code === 200) {
                this.setData({ imageUrl: data.data.url });
                wx.showToast({
                  title: '上传成功',
                  icon: 'success'
                });
              } else {
                wx.showToast({
                  title: data.message || '上传失败',
                  icon: 'none'
                });
              }
            } catch (e) {
              wx.showToast({
                title: '上传失败',
                icon: 'none'
              });
            }
          },
          fail: () => {
            wx.hideLoading();
            // 如果上传失败，在演示模式下使用本地路径
            if (app.globalData.isDemoMode) {
              this.setData({ imageUrl: tempFilePath });
              wx.showToast({
                title: '演示模式：使用本地图片',
                icon: 'none'
              });
            } else {
              wx.showToast({
                title: '上传失败，请重试',
                icon: 'none'
              });
            }
          }
        });
      }
    });
  },

  // 保存菜单
  onSave() {
    if (!this.data.name) {
      wx.showToast({ title: '请输入菜单名称', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    const params = {
      menuType: this.data.menuType,
      name: this.data.name,
      location: this.data.location,
      averageCost: this.data.averageCost,
      recommendedDishes: this.data.recommendedDishes,
      notes: this.data.notes,
      imageUrl: this.data.imageUrl
    };

    const apiMethod = this.data.isEdit
      ? api.updateMenu({ ...params, id: this.data.menuId })
      : api.addMenu(params);

    apiMethod.then(() => {
      app.showSuccess(this.data.isEdit ? '修改成功' : '添加成功');
      setTimeout(() => wx.navigateBack(), 1500);
    }).catch(() => {
      this.setData({ loading: false });
    });
  }
});