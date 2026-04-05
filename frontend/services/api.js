/**
 * API服务层 - 支持演示模式
 */
const app = getApp();

// 演示模式数据管理
const getDemoData = () => {
  const stored = wx.getStorageSync('demoData');
  if (stored) {
    return stored;
  }

  // 默认演示数据
  return {
    userInfo: {
      id: 'demo_user_1',
      nickName: '演示用户',
      avatarUrl: '/assets/images/default-avatar.png',
      coupleCode: 'DEMO1234'
    },
    coupleInfo: {
      id: 'demo_couple_1',
      coupleCode: 'DEMO5678',
      partnerName: '亲爱的TA',
      partnerAvatar: '/assets/images/default-avatar.png',
      startDate: '2024-01-01'
    },
    menuList: [
      { id: 1, name: '海底捞火锅', location: '朝阳区三里屯', menuType: 'wantToGo', averageCost: '150元', statusText: '想去', imageUrl: '', recommendedDishes: '虾滑、毛肚', notes: '约会首选', likeCount: 0, isLiked: false },
      { id: 2, name: '西贝莜面村', location: '海淀区中关村', menuType: 'beenTo', averageCost: '80元', statusText: '去过', imageUrl: '', recommendedDishes: '莜面鱼鱼', notes: '', likeCount: 0, isLiked: false },
      { id: 3, name: '喜茶', location: '朝阳区大悦城', menuType: 'recommended', averageCost: '35元', statusText: '推荐', imageUrl: '', recommendedDishes: '多肉葡萄', notes: '每周必喝', likeCount: 0, isLiked: false }
    ],
    anniversaryList: [
      { id: 1, name: '在一起纪念日', date: '2024-01-01', days: 444 },
      { id: 2, name: '第一次约会', date: '2024-02-14', days: 400 }
    ],
    noteList: [
      { id: 1, title: '周末探店', content: '今天去了一家很棒的餐厅，环境很好，菜品也很不错。', images: [], createTime: '2024-03-01' },
      { id: 2, title: '纪念日晚餐', content: '为TA准备的惊喜晚餐，很成功！', images: [], createTime: '2024-02-14' }
    ],
    feedList: [
      { id: 1, feedType: 'meal', content: '今天请你吃大餐！', senderName: '亲爱的TA', senderAvatar: '', createTime: '今天 12:30', status: 1 },
      { id: 2, feedType: 'dessert', content: '下午茶时间到~', senderName: '亲爱的TA', senderAvatar: '', createTime: '昨天 15:00', status: 0 }
    ],
    wishList: [
      { id: 1, title: '一起去日本旅游', description: '吃正宗的寿司', fulfilled: false, createTime: '2024-01-15' },
      { id: 2, title: '学会做蛋糕', description: '给TA生日礼物', fulfilled: true, createTime: '2024-01-01' }
    ],
    todayFeedStatus: {
      sentToday: false,
      receivedToday: true
    },
    loveTimer: {
      days: 444,
      hours: 8,
      minutes: 30,
      seconds: 15,
      startDate: '2024-01-01'
    }
  };
};

const saveDemoData = (data) => {
  wx.setStorageSync('demoData', data);
};

const demoData = getDemoData();

// 创建延迟的Promise（模拟网络请求）
const delay = (ms = 500) => new Promise(resolve => setTimeout(resolve, ms));

// 演示模式API
const demoApi = {
  // 用户模块
  login(data) {
    return delay().then(() => ({ code: 200, data: { token: 'demo_token', userInfo: demoData.userInfo } }));
  },
  getUserInfo() {
    return delay().then(() => ({ code: 200, data: demoData.userInfo }));
  },
  updateUserInfo(data) {
    return delay().then(() => ({ code: 200, data: { ...demoData.userInfo, ...data } }));
  },

  // 情侣模块
  generateCoupleCode() {
    return delay().then(() => ({ code: 200, data: { coupleCode: 'DEMO5678' } }));
  },
  bindCouple(data) {
    return delay().then(() => ({ code: 200, data: demoData.coupleInfo }));
  },
  getCoupleInfo() {
    return delay().then(() => ({ code: 200, data: demoData.coupleInfo }));
  },
  getCoupleHome() {
    const menuCount = demoData.menuList.length;
    const noteCount = demoData.noteList.length;
    const feedCount = demoData.feedList.length;
    const upcomingAnniversary = demoData.anniversaryList.length > 0
      ? { name: demoData.anniversaryList[0].name, days: demoData.anniversaryList[0].days }
      : null;

    return delay().then(() => ({
      code: 200,
      data: {
        menuCount,
        noteCount,
        feedCount,
        upcomingAnniversary
      }
    }));
  },
  validateCoupleCode(code) {
    return delay().then(() => ({ code: 200, data: { valid: true, partnerName: '亲爱的TA' } }));
  },
  getLoveTimer() {
    return delay().then(() => ({ code: 200, data: demoData.loveTimer }));
  },

  // 菜单模块
  getMenuList(params) {
    return delay().then(() => ({ code: 200, data: demoData.menuList }));
  },
  getMenuDetail(id) {
    const menu = demoData.menuList.find(m => m.id == id) || demoData.menuList[0];
    return delay().then(() => ({ code: 200, data: menu }));
  },
  addMenu(data) {
    const newMenu = { id: Date.now(), ...data, likeCount: 0, isLiked: false };
    demoData.menuList.push(newMenu);
    saveDemoData(demoData);
    return delay().then(() => ({ code: 200, data: newMenu }));
  },
  updateMenu(id, data) {
    const index = demoData.menuList.findIndex(m => m.id == id);
    if (index !== -1) {
      demoData.menuList[index] = { ...demoData.menuList[index], ...data };
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200, data: { id, ...data } }));
  },
  deleteMenu(id) {
    const index = demoData.menuList.findIndex(m => m.id == id);
    if (index !== -1) {
      demoData.menuList.splice(index, 1);
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },
  recoverMenu(id) {
    return delay().then(() => ({ code: 200 }));
  },
  likeMenu(id) {
    const menu = demoData.menuList.find(m => m.id == id);
    if (menu) {
      if (menu.isLiked) {
        menu.likeCount = Math.max((menu.likeCount || 0) - 1, 0);
        menu.isLiked = false;
      } else {
        menu.likeCount = (menu.likeCount || 0) + 1;
        menu.isLiked = true;
      }
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },
  favoriteMenu(id) {
    return delay().then(() => ({ code: 200 }));
  },
  getMenuStats() {
    const wantToGoCount = demoData.menuList.filter(m => m.menuType === 'wantToGo').length;
    const beenToCount = demoData.menuList.filter(m => m.menuType === 'beenTo').length;
    const recommendedCount = demoData.menuList.filter(m => m.menuType === 'recommended').length;
    return delay().then(() => ({ code: 200, data: { wantToGoCount, beenToCount, recommendedCount } }));
  },

  // 纪念日模块
  getAnniversaryList() {
    return delay().then(() => ({ code: 200, data: demoData.anniversaryList }));
  },
  getUpcomingAnniversaries() {
    return delay().then(() => ({ code: 200, data: demoData.anniversaryList }));
  },
  getNextAnniversary() {
    return delay().then(() => ({ code: 200, data: demoData.anniversaryList[0] }));
  },
  addAnniversary(data) {
    const newAnniversary = { id: Date.now(), ...data, days: 0 };
    demoData.anniversaryList.push(newAnniversary);
    saveDemoData(demoData);
    return delay().then(() => ({ code: 200, data: newAnniversary }));
  },
  updateAnniversary(id, data) {
    const index = demoData.anniversaryList.findIndex(a => a.id == id);
    if (index !== -1) {
      demoData.anniversaryList[index] = { ...demoData.anniversaryList[index], ...data };
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200, data: { id, ...data } }));
  },
  deleteAnniversary(id) {
    const index = demoData.anniversaryList.findIndex(a => a.id == id);
    if (index !== -1) {
      demoData.anniversaryList.splice(index, 1);
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },

  // 投喂模块
  getTodayFeedStatus() {
    return delay().then(() => ({ code: 200, data: demoData.todayFeedStatus }));
  },
  sendFeed(data) {
    const newFeed = { id: Date.now(), ...data };
    demoData.todayFeedStatus.sentToday = true;
    saveDemoData(demoData);
    return delay().then(() => ({ code: 200, data: newFeed }));
  },
  getReceivedFeeds() {
    return delay().then(() => ({ code: 200, data: demoData.feedList }));
  },
  getSentFeeds() {
    return delay().then(() => ({ code: 200, data: [] }));
  },
  acceptFeed(id) {
    const feed = demoData.feedList.find(f => f.id == id);
    if (feed) {
      feed.status = 1;  // 1表示已接受
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },
  rejectFeed(id, reason) {
    const feed = demoData.feedList.find(f => f.id == id);
    if (feed) {
      feed.status = 2;  // 2表示已拒绝
      feed.rejectReason = reason;
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },

  // 笔记模块
  getNoteList(params) {
    return delay().then(() => ({ code: 200, data: demoData.noteList }));
  },
  getNoteDetail(id) {
    const note = demoData.noteList.find(n => n.id == id) || demoData.noteList[0];
    return delay().then(() => ({ code: 200, data: note }));
  },
  addNote(data) {
    const newNote = { id: Date.now(), ...data, createTime: new Date().toLocaleDateString() };
    demoData.noteList.unshift(newNote);
    saveDemoData(demoData);
    return delay().then(() => ({ code: 200, data: newNote }));
  },
  updateNote(id, data) {
    const index = demoData.noteList.findIndex(n => n.id == id);
    if (index !== -1) {
      demoData.noteList[index] = { ...demoData.noteList[index], ...data };
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200, data: { id, ...data } }));
  },
  deleteNote(id) {
    const index = demoData.noteList.findIndex(n => n.id == id);
    if (index !== -1) {
      demoData.noteList.splice(index, 1);
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },
  likeNote(id) {
    return delay().then(() => ({ code: 200 }));
  },
  commentNote(id, content) {
    return delay().then(() => ({ code: 200, data: { id: Date.now(), content } }));
  },

  // 通知模块
  getNotificationList(params) {
    return delay().then(() => ({ code: 200, data: [] }));
  },
  getUnreadCount() {
    return delay().then(() => ({ code: 200, data: 0 }));
  },
  markAsRead(id) {
    return delay().then(() => ({ code: 200 }));
  },
  markAllAsRead() {
    return delay().then(() => ({ code: 200 }));
  },

  // 心愿单模块
  getWishList() {
    return delay().then(() => ({ code: 200, data: demoData.wishList }));
  },
  addWish(data) {
    const newWish = { id: Date.now(), ...data, fulfilled: false, createTime: new Date().toLocaleDateString() };
    demoData.wishList.unshift(newWish);
    saveDemoData(demoData);
    return delay().then(() => ({ code: 200, data: newWish }));
  },
  fulfillWish(id) {
    const wish = demoData.wishList.find(w => w.id == id);
    if (wish) {
      wish.fulfilled = true;
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },
  deleteWish(id) {
    const index = demoData.wishList.findIndex(w => w.id == id);
    if (index !== -1) {
      demoData.wishList.splice(index, 1);
      saveDemoData(demoData);
    }
    return delay().then(() => ({ code: 200 }));
  },

  // 相册模块
  getPhotoList() {
    return delay().then(() => ({ code: 200, data: [] }));
  },
  uploadPhotos(data) {
    return delay().then(() => ({ code: 200, data: { urls: data.urls } }));
  },
  deletePhoto(id) {
    return delay().then(() => ({ code: 200 }));
  },

  // 食谱模块
  getRecipeList() {
    return delay().then(() => ({ code: 200, data: [] }));
  },

  // 厨师订单模块
  getChefOrderList(params) {
    return delay().then(() => ({ code: 200, data: [] }));
  },
  processChefOrder(id) {
    return delay().then(() => ({ code: 200 }));
  },
  completeChefOrder(id) {
    return delay().then(() => ({ code: 200 }));
  }
};

const api = {
  // 检查是否演示模式
  isDemoMode() {
    return app.globalData.isDemoMode;
  },

  // 统一请求方法
  request(options) {
    // 演示模式下使用模拟数据
    if (this.isDemoMode()) {
      return this.handleDemoRequest(options);
    }
    return app.request(options);
  },

  // 处理演示模式请求
  handleDemoRequest(options) {
    const { url, method = 'GET', data = {} } = options;
    console.log(`[Demo Mode] ${method} ${url}`, data);

    // 简单路由匹配
    if (url.includes('/user/login') && method === 'POST') {
      return demoApi.login(data);
    }
    if (url === '/user/info' || url === '/user/update') {
      return method === 'GET' ? demoApi.getUserInfo() : demoApi.updateUserInfo(data);
    }
    if (url === '/couple/info' || url === '/couple/home') {
      return url === '/couple/home' ? demoApi.getCoupleHome() : demoApi.getCoupleInfo();
    }
    if (url === '/couple/generateCode' && method === 'POST') {
      return demoApi.generateCoupleCode();
    }
    if (url === '/couple/bind' && method === 'POST') {
      return demoApi.bindCouple(data);
    }
    if (url === '/couple/validateCode') {
      return demoApi.validateCoupleCode(data.coupleCode);
    }
    if (url === '/couple/loveTimer') {
      return demoApi.getLoveTimer();
    }
    if (url.startsWith('/menu/list')) {
      return demoApi.getMenuList(data);
    }
    if (url.startsWith('/menu/detail/')) {
      const id = url.split('/').pop();
      return demoApi.getMenuDetail(id);
    }
    if (url === '/menu/add' && method === 'POST') {
      return demoApi.addMenu(data);
    }
    if (url.startsWith('/menu/update/') && method === 'PUT') {
      const id = url.split('/').pop();
      return demoApi.updateMenu(id, data);
    }
    if (url.startsWith('/menu/delete/') && method === 'DELETE') {
      const id = url.split('/').pop();
      return demoApi.deleteMenu(id);
    }
    if (url === '/menu/stats') {
      return demoApi.getMenuStats();
    }
    if (url === '/anniversary/list' || url === '/anniversary/upcoming' || url === '/anniversary/next') {
      if (url === '/anniversary/next') return demoApi.getNextAnniversary();
      if (url === '/anniversary/upcoming') return demoApi.getUpcomingAnniversaries();
      return demoApi.getAnniversaryList();
    }
    if (url === '/anniversary/add' && method === 'POST') {
      return demoApi.addAnniversary(data);
    }
    if (url.startsWith('/anniversary/delete/') && method === 'DELETE') {
      const id = url.split('/').pop();
      return demoApi.deleteAnniversary(id);
    }
    if (url === '/feed/today') {
      return demoApi.getTodayFeedStatus();
    }
    if (url === '/feed/send' && method === 'POST') {
      return demoApi.sendFeed(data);
    }
    if (url === '/feed/received') {
      return demoApi.getReceivedFeeds();
    }
    if (url === '/feed/sent') {
      return demoApi.getSentFeeds();
    }
    if (url.startsWith('/feed/accept/') && method === 'POST') {
      const id = url.split('/').pop();
      return demoApi.acceptFeed(id);
    }
    if (url.startsWith('/feed/reject/') && method === 'POST') {
      const id = url.split('/').pop();
      return demoApi.rejectFeed(id, data.reason);
    }
    if (url === '/note/list') {
      return demoApi.getNoteList(data);
    }
    if (url.startsWith('/note/detail/')) {
      const id = url.split('/').pop();
      return demoApi.getNoteDetail(id);
    }
    if (url === '/note/add' && method === 'POST') {
      return demoApi.addNote(data);
    }
    if (url.startsWith('/note/delete/') && method === 'DELETE') {
      const id = url.split('/').pop();
      return demoApi.deleteNote(id);
    }
    if (url === '/notification/list') {
      return demoApi.getNotificationList(data);
    }
    if (url === '/notification/unreadCount') {
      return demoApi.getUnreadCount();
    }

    // 默认延迟响应
    return delay().then(() => ({ code: 200, data: {} }));
  },

  // ========== 用户模块 ==========
  login(data) {
    return this.request({ url: '/user/login', method: 'POST', data });
  },
  getUserInfo() {
    return this.request({ url: '/user/info', method: 'GET' });
  },
  updateUserInfo(data) {
    return this.request({ url: '/user/update', method: 'PUT', data });
  },

  // ========== 情侣模块 ==========
  generateCoupleCode(data) {
    return this.request({ url: '/couple/generateCode', method: 'POST', data });
  },
  bindCouple(data) {
    return this.request({ url: '/couple/bind', method: 'POST', data });
  },
  getCoupleInfo() {
    return this.request({ url: '/couple/info', method: 'GET' });
  },
  getCoupleHome() {
    return this.request({ url: '/couple/home', method: 'GET' });
  },
  applyUnbind(data) {
    return this.request({ url: '/couple/unbind/apply', method: 'POST', data });
  },
  confirmUnbind(coupleId) {
    return this.request({ url: '/couple/unbind/confirm', method: 'POST', data: { coupleId } });
  },
  rejectUnbind(coupleId) {
    return this.request({ url: '/couple/unbind/reject', method: 'POST', data: { coupleId } });
  },
  validateCoupleCode(coupleCode) {
    return this.request({ url: '/couple/validateCode', method: 'GET', data: { coupleCode } });
  },
  getLoveTimer() {
    return this.request({ url: '/couple/loveTimer', method: 'GET' });
  },

  // ========== 菜单模块 ==========
  getMenuList(params) {
    return this.request({ url: '/menu/list', method: 'GET', data: params });
  },
  getMenuDetail(id) {
    return this.request({ url: `/menu/detail/${id}`, method: 'GET' });
  },
  addMenu(data) {
    return this.request({ url: '/menu/add', method: 'POST', data });
  },
  updateMenu(data) {
    return this.request({ url: `/menu/update/${data.id}`, method: 'PUT', data });
  },
  deleteMenu(id) {
    return this.request({ url: `/menu/delete/${id}`, method: 'DELETE' });
  },
  recoverMenu(id) {
    return this.request({ url: `/menu/recover/${id}`, method: 'POST' });
  },
  likeMenu(id) {
    return this.request({ url: `/menu/like/${id}`, method: 'POST' });
  },
  favoriteMenu(id) {
    return this.request({ url: `/menu/favorite/${id}`, method: 'POST' });
  },
  getMenuStats() {
    return this.request({ url: '/menu/stats', method: 'GET' });
  },

  // ========== 纪念日模块 ==========
  getAnniversaryList() {
    return this.request({ url: '/anniversary/list', method: 'GET' });
  },
  getUpcomingAnniversaries() {
    return this.request({ url: '/anniversary/upcoming', method: 'GET' });
  },
  getNextAnniversary() {
    return this.request({ url: '/anniversary/next', method: 'GET' });
  },
  addAnniversary(data) {
    return this.request({ url: '/anniversary/add', method: 'POST', data });
  },
  updateAnniversary(id, data) {
    return this.request({ url: `/anniversary/update/${id}`, method: 'PUT', data });
  },
  deleteAnniversary(id) {
    return this.request({ url: `/anniversary/delete/${id}`, method: 'DELETE' });
  },

  // ========== 投喂模块 ==========
  getTodayFeedStatus() {
    return this.request({ url: '/feed/today', method: 'GET' });
  },
  sendFeed(data) {
    return this.request({ url: '/feed/send', method: 'POST', data });
  },
  getReceivedFeeds() {
    return this.request({ url: '/feed/received', method: 'GET' });
  },
  getSentFeeds() {
    return this.request({ url: '/feed/sent', method: 'GET' });
  },
  acceptFeed(id) {
    return this.request({ url: `/feed/accept/${id}`, method: 'POST' });
  },
  rejectFeed(id, reason) {
    return this.request({ url: `/feed/reject/${id}`, method: 'POST', data: { reason } });
  },

  // ========== 笔记模块 ==========
  getNoteList(params) {
    return this.request({ url: '/note/list', method: 'GET', data: params });
  },
  getNoteDetail(id) {
    return this.request({ url: `/note/detail/${id}`, method: 'GET' });
  },
  addNote(data) {
    return this.request({ url: '/note/add', method: 'POST', data });
  },
  updateNote(id, data) {
    return this.request({ url: `/note/update/${id}`, method: 'PUT', data });
  },
  deleteNote(id) {
    return this.request({ url: `/note/delete/${id}`, method: 'DELETE' });
  },
  likeNote(id) {
    return this.request({ url: `/note/like/${id}`, method: 'POST' });
  },
  commentNote(id, content) {
    return this.request({ url: `/note/comment/${id}`, method: 'POST', data: { content } });
  },

  // ========== 通知模块 ==========
  getNotificationList(params) {
    return this.request({ url: '/notification/list', method: 'GET', data: params });
  },
  getUnreadCount() {
    return this.request({ url: '/notification/unreadCount', method: 'GET' });
  },
  markAsRead(id) {
    return this.request({ url: `/notification/read/${id}`, method: 'PUT' });
  },
  markAllAsRead() {
    return this.request({ url: '/notification/readAll', method: 'PUT' });
  },

  // ========== 心愿单模块 ==========
  getWishList() {
    return this.request({ url: '/wish/list', method: 'GET' });
  },
  addWish(data) {
    return this.request({ url: '/wish/add', method: 'POST', data });
  },
  fulfillWish(id) {
    return this.request({ url: `/wish/fulfill/${id}`, method: 'POST' });
  },
  deleteWish(id) {
    return this.request({ url: `/wish/delete/${id}`, method: 'DELETE' });
  },

  // ========== 相册模块 ==========
  getPhotoList() {
    return this.request({ url: '/photo/list', method: 'GET' });
  },
  uploadPhotos(data) {
    return this.request({ url: '/photo/upload', method: 'POST', data });
  },
  deletePhoto(id) {
    return this.request({ url: `/photo/delete/${id}`, method: 'DELETE' });
  },

  // ========== 食谱模块 ==========
  getRecipeList() {
    return this.request({ url: '/recipe/list', method: 'GET' });
  },

  // ========== 厨师订单模块 ==========
  getChefOrderList(params) {
    return this.request({ url: '/chef/order/list', method: 'GET', data: params });
  },
  processChefOrder(id) {
    return this.request({ url: `/chef/order/process/${id}`, method: 'POST' });
  },
  completeChefOrder(id) {
    return this.request({ url: `/chef/order/complete/${id}`, method: 'POST' });
  }
};

module.exports = api;