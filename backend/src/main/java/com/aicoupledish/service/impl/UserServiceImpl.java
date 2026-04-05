package com.aicoupledish.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.LoginRespDTO;
import com.aicoupledish.domain.dto.UserInfoDTO;
import com.aicoupledish.domain.req.WechatLoginReq;
import com.aicoupledish.service.CoupleService;
import com.aicoupledish.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 用户服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {

    private final UserMapper userMapper;
    private final JwtUtils jwtUtils;
    private final RedisTemplate<String, String> redisTemplate;

    @Autowired(required = false)
    private CoupleService coupleService;

    private static final String USER_CACHE_PREFIX = "user:info:";
    private static final String OPENID_CACHE_PREFIX = "user:openid:";
    private static final String VERIFY_CODE_PREFIX = "user:verify:code:";
    private static final String VERIFY_CODE_EXPIRE_PREFIX = "user:verify:expire:";

    // 使用安全的随机数生成器
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    @Override
    public LoginRespDTO wechatLogin(WechatLoginReq req) {
        // 模拟微信登录，实际项目中需要调用微信接口获取openid
        String openid = req.getCode();
        if (StrUtil.isBlank(openid)) {
            throw BusinessException.USER_NOT_LOGGED_IN;
        }

        // 查找或创建用户
        User user = findOrCreateUser(openid, req.getNickName(), req.getAvatarUrl());

        // 生成Token
        String token = jwtUtils.generateToken(user.getId());

        // 构建返回
        LoginRespDTO resp = new LoginRespDTO();
        resp.setToken(token);
        resp.setUserInfo(buildUserInfoDTO(user));

        return resp;
    }

    /**
     * 手机号登录
     * 注意: 此接口仅用于开发测试环境，生产环境请使用微信登录
     * 生产环境应通过profile控制禁用此方法
     */
    @Override
    public LoginRespDTO phoneLogin(String phone) {
        // 生产环境安全检查：验证手机号格式
        if (phone == null || !phone.matches("^1[3-9]\\d{9}$")) {
            throw new IllegalArgumentException("手机号格式不正确");
        }

        // 安全警告：此接口在生产环境应禁用或添加短信验证码验证
        log.warn("手机号登录接口调用，生产环境应禁用此接口: phone={}", phone.replaceAll("(\\d{3})\\d{4}(\\d{4})", "$1****$2"));
        // 本地开发模式：根据手机号查找用户
        User user = userMapper.selectOne(
            new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                .eq(User::getPhone, phone)
        );

        if (user == null) {
            // 如果用户不存在，创建一个新用户（本地开发模式）
            user = new User();
            user.setPhone(phone);
            user.setOpenid("phone_" + phone);
            user.setNickName("用户" + phone.substring(phone.length() - 4));
            user.setStatus(0);
            user.setMemberLevel(0);
            userMapper.insert(user);
            log.info("手机号登录创建新用户: phone={}, userId={}", phone, user.getId());
        }

        // 生成Token
        String token = jwtUtils.generateToken(user.getId());

        // 构建返回
        LoginRespDTO resp = new LoginRespDTO();
        resp.setToken(token);
        resp.setUserInfo(buildUserInfoDTO(user));

        return resp;
    }

    @Override
    public void sendVerifyCode(String phone) {
        // 验证手机号格式
        if (StrUtil.isBlank(phone) || !phone.matches("^1[3-9]\\d{9}$")) {
            throw new IllegalArgumentException("手机号格式不正确");
        }

        // 检查发送频率限制（60秒内只能发送一次）
        String expireKey = VERIFY_CODE_EXPIRE_PREFIX + phone;
        String lastSendTime = redisTemplate.opsForValue().get(expireKey);
        if (lastSendTime != null) {
            throw BusinessException.OPERATION_TOO_FREQUENT;
        }

        // 生成6位验证码（使用安全随机数）
        int codeInt = SECURE_RANDOM.nextInt(900000) + 100000; // 100000-999999
        String code = String.valueOf(codeInt);

        // 存储验证码，有效期5分钟
        String codeKey = VERIFY_CODE_PREFIX + phone;
        redisTemplate.opsForValue().set(codeKey, code, 5, TimeUnit.MINUTES);

        // 设置发送频率限制
        redisTemplate.opsForValue().set(expireKey, "1", 60, TimeUnit.SECONDS);

        // 实际项目中这里应该调用短信服务发送验证码
        // smsService.sendVerifyCode(phone, code);

        log.info("发送验证码: phone={}", phone);
    }

    @Override
    public UserInfoDTO getUserInfo(Long userId) {
        User user = getUserById(userId);
        return buildUserInfoDTO(user);
    }

    @Override
    public void updateUserInfo(Long userId, String nickName, String avatarUrl) {
        User user = getUserById(userId);
        if (StrUtil.isNotBlank(nickName)) {
            user.setNickName(nickName);
        }
        if (StrUtil.isNotBlank(avatarUrl)) {
            user.setAvatarUrl(avatarUrl);
        }
        userMapper.updateById(user);

        // 清除缓存
        redisTemplate.delete(USER_CACHE_PREFIX + userId);
    }

    @Override
    public Long getUserIdByOpenid(String openid) {
        String cached = redisTemplate.opsForValue().get(OPENID_CACHE_PREFIX + openid);
        if (cached != null) {
            return Long.parseLong(cached);
        }

        User user = userMapper.selectOne(
            new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                .eq(User::getOpenid, openid)
        );

        if (user != null) {
            redisTemplate.opsForValue().set(
                OPENID_CACHE_PREFIX + openid,
                user.getId().toString(),
                7, TimeUnit.DAYS
            );
            return user.getId();
        }
        return null;
    }

    @Override
    public User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        return user;
    }

    @Override
    public Map<Long, User> getUsersByIds(Collection<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return new java.util.HashMap<>();
        }
        List<User> users = userMapper.selectBatchIds(userIds);
        return users.stream().collect(java.util.stream.Collectors.toMap(User::getId, u -> u, (a, b) -> a));
    }

    private User findOrCreateUser(String openid, String nickName, String avatarUrl) {
        User user = userMapper.selectOne(
            new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                .eq(User::getOpenid, openid)
        );

        if (user == null) {
            user = new User();
            user.setOpenid(openid);
            user.setNickName(StrUtil.isNotBlank(nickName) ? nickName : "用户" + System.currentTimeMillis() % 10000);
            user.setAvatarUrl(StrUtil.isNotBlank(avatarUrl) ? avatarUrl : "");
            user.setStatus(0);
            user.setMemberLevel(0);
            userMapper.insert(user);
            log.info("创建新用户: openid={}, userId={}", openid, user.getId());
        } else {
            // 更新用户信息
            if (StrUtil.isNotBlank(nickName)) {
                user.setNickName(nickName);
            }
            if (StrUtil.isNotBlank(avatarUrl)) {
                user.setAvatarUrl(avatarUrl);
            }
            userMapper.updateById(user);
        }

        // 缓存openid映射
        redisTemplate.opsForValue().set(
            OPENID_CACHE_PREFIX + openid,
            user.getId().toString(),
            7, TimeUnit.DAYS
        );

        return user;
    }

    private UserInfoDTO buildUserInfoDTO(User user) {
        UserInfoDTO dto = new UserInfoDTO();
        dto.setId(user.getId());
        dto.setOpenid(user.getOpenid());
        dto.setNickName(user.getNickName());
        dto.setAvatarUrl(user.getAvatarUrl());
        dto.setPhone(user.getPhone());
        dto.setGender(user.getGender());
        dto.setCoupleId(user.getCoupleId());
        dto.setMemberLevel(user.getMemberLevel());
        dto.setStatus(user.getStatus());

        if (user.getLoveStartDate() != null) {
            dto.setLoveStartDate(user.getLoveStartDate().toString());
        }

        // 如果有情侣关系，填充情侣信息
        if (user.getCoupleId() != null && coupleService != null) {
            try {
                dto.setCoupleInfo(coupleService.getCoupleInfo(user.getId()));
            } catch (Exception e) {
                log.warn("获取情侣信息失败: userId={}", user.getId(), e);
            }
        }

        return dto;
    }
}