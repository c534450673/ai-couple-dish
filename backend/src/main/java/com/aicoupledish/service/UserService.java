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
     * 微信登录
     */
    LoginRespDTO wechatLogin(WechatLoginReq req);

    /**
     * 手机号登录（本地开发用）
     */
    LoginRespDTO phoneLogin(String phone);

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
}