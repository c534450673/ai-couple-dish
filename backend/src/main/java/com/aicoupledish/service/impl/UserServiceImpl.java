package com.aicoupledish.service.impl;

import cn.hutool.core.util.StrUtil;
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
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

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
    private final CoupleService coupleService;

    private static final String USER_CACHE_PREFIX = "user:info:";
    private static final String OPENID_CACHE_PREFIX = "user:openid:";
    private static final String VERIFY_CODE_PREFIX = "user:verify:code:";
    private static final String VERIFY_CODE_EXPIRE_PREFIX = "user:verify:expire:";

    private static final int DEFAULT_USER_STATUS = 0;
    private static final int DEFAULT_MEMBER_LEVEL = 0;
    private static final long VERIFY_CODE_TTL_MINUTES = 5;
    private static final long VERIFY_CODE_RATE_LIMIT_SECONDS = 60;
    private static final long OPENID_CACHE_TTL_DAYS = 7;

    private static final Pattern PHONE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    @Override
    public LoginRespDTO wechatLogin(WechatLoginReq req) {
        String openid = req.getCode();
        if (StrUtil.isBlank(openid)) {
            throw BusinessException.USER_NOT_LOGGED_IN;
        }

        User user = findOrCreateUserByOpenid(openid, req.getNickName(), req.getAvatarUrl());
        return buildLoginResponse(user);
    }

    @Override
    public LoginRespDTO registerByPhone(String phone, String verifyCode) {
        if (!isValidPhoneNumber(phone)) {
            throw new BusinessException(1004, "手机号格式不正确");
        }

        validateVerifyCode(phone, verifyCode);

        Optional<User> existingUser = findUserByPhone(phone);
        if (existingUser.isPresent()) {
            throw new BusinessException(1005, "该手机号已注册，请直接登录");
        }

        User newUser = createNewPhoneUser(phone);
        log.info("手机号注册创建新用户: phone={}, userId={}", maskPhone(phone), newUser.getId());

        // 验证成功后删除验证码，防止重复使用
        deleteVerifyCode(phone);

        return buildLoginResponse(newUser);
    }

    @Override
    public LoginRespDTO phoneLogin(String phone, String verifyCode) {
        if (!isValidPhoneNumber(phone)) {
            throw new BusinessException(1004, "手机号格式不正确");
        }

        // 验证验证码
        validateVerifyCode(phone, verifyCode);

        User user = findUserByPhone(phone)
                .orElseThrow(() -> new BusinessException(1006, "该手机号未注册，请先注册"));

        // 验证成功后删除验证码
        deleteVerifyCode(phone);

        return buildLoginResponse(user);
    }

    private void validateVerifyCode(String phone, String verifyCode) {
        if (StrUtil.isBlank(verifyCode)) {
            throw new BusinessException(9003, "验证码不能为空");
        }

        String codeKey = VERIFY_CODE_PREFIX + phone;
        String storedCode = redisTemplate.opsForValue().get(codeKey);

        if (storedCode == null) {
            throw new BusinessException(9004, "验证码已过期，请重新获取");
        }

        if (!storedCode.equals(verifyCode)) {
            throw new BusinessException(9003, "验证码错误");
        }
    }

    private void deleteVerifyCode(String phone) {
        String codeKey = VERIFY_CODE_PREFIX + phone;
        redisTemplate.delete(codeKey);
        String expireKey = VERIFY_CODE_EXPIRE_PREFIX + phone;
        redisTemplate.delete(expireKey);
    }

    @Override
    public void sendVerifyCode(String phone) {
        if (!isValidPhoneNumber(phone)) {
            throw new BusinessException(1004, "手机号格式不正确");
        }

        String expireKey = VERIFY_CODE_EXPIRE_PREFIX + phone;
        if (redisTemplate.opsForValue().get(expireKey) != null) {
            throw BusinessException.OPERATION_TOO_FREQUENT;
        }

        String code = generateSecureCode();
        String codeKey = VERIFY_CODE_PREFIX + phone;
        redisTemplate.opsForValue().set(codeKey, code, VERIFY_CODE_TTL_MINUTES, TimeUnit.MINUTES);
        redisTemplate.opsForValue().set(expireKey, "1", VERIFY_CODE_RATE_LIMIT_SECONDS, TimeUnit.SECONDS);

        log.info("发送验证码: phone={}", maskPhone(phone));
    }

    @Override
    public boolean isValidPhoneNumber(String phone) {
        return phone != null && PHONE_PATTERN.matcher(phone).matches();
    }

    @Override
    public UserInfoDTO getUserInfo(Long userId) {
        User user = getUserById(userId);
        return buildUserInfoDTO(user);
    }

    @Override
    public void updateUserInfo(Long userId, String nickName, String avatarUrl) {
        User user = getUserById(userId);
        boolean shouldUpdate = false;

        if (StrUtil.isNotBlank(nickName)) {
            user.setNickName(nickName);
            shouldUpdate = true;
        }
        if (StrUtil.isNotBlank(avatarUrl)) {
            user.setAvatarUrl(avatarUrl);
            shouldUpdate = true;
        }

        if (shouldUpdate) {
            userMapper.updateById(user);
            redisTemplate.delete(USER_CACHE_PREFIX + userId);
        }
    }

    @Override
    public Long getUserIdByOpenid(String openid) {
        String cached = redisTemplate.opsForValue().get(OPENID_CACHE_PREFIX + openid);
        if (cached != null) {
            return Long.parseLong(cached);
        }

        User user = findUserByOpenid(openid);
        if (user == null) {
            return null;
        }

        cacheOpenidMapping(openid, user.getId());
        return user.getId();
    }

    @Override
    public User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    @Override
    public Map<Long, User> getUsersByIds(Collection<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return Map.of();
        }
        List<User> users = userMapper.selectBatchIds(userIds);
        return users.stream().collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));
    }

    // ========== Private helper methods ==========

    private User findOrCreateUserByOpenid(String openid, String nickName, String avatarUrl) {
        User existingUser = findUserByOpenid(openid);
        if (existingUser != null) {
            updateExistingUserProfile(existingUser, nickName, avatarUrl);
            return existingUser;
        }
        return createNewWechatUser(openid, nickName, avatarUrl);
    }

    private User createNewWechatUser(String openid, String nickName, String avatarUrl) {
        User user = new User();
        user.setOpenid(openid);
        user.setNickName(StrUtil.isNotBlank(nickName) ? nickName : "用户" + System.currentTimeMillis() % 10000);
        user.setAvatarUrl(StrUtil.isNotBlank(avatarUrl) ? avatarUrl : "");
        user.setStatus(DEFAULT_USER_STATUS);
        user.setMemberLevel(DEFAULT_MEMBER_LEVEL);
        userMapper.insert(user);
        cacheOpenidMapping(openid, user.getId());
        log.info("创建新微信用户: openid={}, userId={}", openid, user.getId());
        return user;
    }

    private User createNewPhoneUser(String phone) {
        User user = new User();
        user.setPhone(phone);
        user.setNickName("用户" + phone.substring(phone.length() - 4));
        user.setStatus(DEFAULT_USER_STATUS);
        user.setMemberLevel(DEFAULT_MEMBER_LEVEL);
        userMapper.insert(user);
        return user;
    }

    private void updateExistingUserProfile(User user, String nickName, String avatarUrl) {
        boolean shouldUpdate = false;
        if (StrUtil.isNotBlank(nickName)) {
            user.setNickName(nickName);
            shouldUpdate = true;
        }
        if (StrUtil.isNotBlank(avatarUrl)) {
            user.setAvatarUrl(avatarUrl);
            shouldUpdate = true;
        }
        if (shouldUpdate) {
            userMapper.updateById(user);
        }
    }

    private Optional<User> findUserByPhone(String phone) {
        User user = userMapper.selectOne(
            new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                .eq(User::getPhone, phone)
        );
        return Optional.ofNullable(user);
    }

    private User findUserByOpenid(String openid) {
        return userMapper.selectOne(
            new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User>()
                .eq(User::getOpenid, openid)
        );
    }

    private LoginRespDTO buildLoginResponse(User user) {
        String token = jwtUtils.generateToken(user.getId());
        UserInfoDTO userInfo = buildUserInfoDTO(user);
        return new LoginRespDTO(token, userInfo);
    }

    private void cacheOpenidMapping(String openid, Long userId) {
        redisTemplate.opsForValue().set(
            OPENID_CACHE_PREFIX + openid,
            userId.toString(),
            OPENID_CACHE_TTL_DAYS, TimeUnit.DAYS
        );
    }

    private String generateSecureCode() {
        int codeInt = SECURE_RANDOM.nextInt(900000) + 100000;
        return String.valueOf(codeInt);
    }

    private String maskPhone(String phone) {
        return phone.replaceAll("(\\d{3})\\d{4}(\\d{4})", "$1****$2");
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

        if (user.getCoupleId() != null && coupleService != null) {
            try {
                dto.setCoupleInfo(coupleService.getCoupleInfo(user.getId()));
            } catch (Exception e) {
                log.warn("获取情侣信息失败: userId={}", user.getId(), e);
            }
        }

        return dto;
    }

    @Override
    public void logout(Long userId) {
        if (userId == null) {
            return;
        }
        // 清除用户缓存
        redisTemplate.delete(USER_CACHE_PREFIX + userId);
        log.info("用户退出登录: userId={}", userId);
    }
}
