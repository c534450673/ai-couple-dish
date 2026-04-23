package com.aicoupledish.service;

import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.LoginRespDTO;
import com.aicoupledish.domain.dto.UserInfoDTO;
import com.aicoupledish.domain.req.WechatLoginReq;

import java.util.Collection;
import java.util.Map;

/**
 * 用户服务接口
 */
public interface UserService {

    /**
     * 微信登录（含自动注册）
     */
    LoginRespDTO wechatLogin(WechatLoginReq req);

    /**
     * 手机号注册（创建新用户）
     */
    LoginRespDTO registerByPhone(String phone, String verifyCode);

    /**
     * 手机号登录
     */
    LoginRespDTO phoneLogin(String phone, String verifyCode);

    /**
     * 发送验证码
     */
    void sendVerifyCode(String phone);

    /**
     * 获取用户信息
     */
    UserInfoDTO getUserInfo(Long userId);

    /**
     * 获取用户对象
     */
    User getUserById(Long userId);

    /**
     * 批量获取用户对象
     */
    Map<Long, User> getUsersByIds(Collection<Long> userIds);

    /**
     * 更新用户信息
     */
    void updateUserInfo(Long userId, String nickName, String avatarUrl);

    /**
     * 根据OpenID获取用户
     */
    Long getUserIdByOpenid(String openid);

    /**
     * 验证手机号格式
     */
    boolean isValidPhoneNumber(String phone);

    /**
     * 退出登录（使token缓存失效）
     */
    void logout(Long userId);
}