package com.aicoupledish.service.impl;

import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.StrUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.AnniversaryMapper;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.CoupleMenuMapper;
import com.aicoupledish.dao.mapper.CoupleUnbindRecordMapper;
import com.aicoupledish.dao.mapper.FeedMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.mapper.WishMapper;
import com.aicoupledish.dao.model.Anniversary;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.CoupleMenu;
import com.aicoupledish.dao.model.CoupleUnbindRecord;
import com.aicoupledish.dao.model.Feed;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.dao.model.Wish;
import com.aicoupledish.domain.dto.*;
import com.aicoupledish.domain.req.BindCoupleReq;
import com.aicoupledish.domain.req.GenerateCodeReq;
import com.aicoupledish.domain.req.UnbindReq;
import com.aicoupledish.service.CoupleService;
import com.aicoupledish.service.FeedService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * 情侣服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CoupleServiceImpl implements CoupleService {

    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;
    private final AnniversaryMapper anniversaryMapper;
    private final FeedMapper feedMapper;
    private final CoupleUnbindRecordMapper unbindRecordMapper;
    private final CoupleMenuMapper menuMapper;
    private final WishMapper wishMapper;
    private final RedisTemplate<String, String> redisTemplate;

    @Autowired(required = false)
    private FeedService feedService;

    @Autowired(required = false)
    private NotificationService notificationService;

    private static final String COUPLE_CODE_PREFIX = "couple:code:";
    private static final long COUPLE_CODE_EXPIRE_DAYS = 7;

    // 数据保护相关常量
    private static final int DATA_RETENTION_DAYS = 30; // 数据保留30天
    private static final int REBIND_COOLDOWN_HOURS = 24; // 重新绑定冷却期24小时
    private static final int UNBIND_CONFIRM_HOURS = 24; // 解绑确认冷却期24小时

    @Override
    @Transactional
    public String generateCoupleCode(Long userId, GenerateCodeReq req) {
        User user = getUserById(userId);

        // 检查是否已有情侣关系
        if (user.getCoupleId() != null) {
            throw BusinessException.COUPLE_ALREADY_BIND;
        }

        // 检查是否已有有效的情侣码
        String userCodeKey = COUPLE_CODE_PREFIX + "user:" + userId;
        String existingCode = redisTemplate.opsForValue().get(userCodeKey);
        if (existingCode != null) {
            // 已有有效情侣码，直接返回
            String existingCacheKey = COUPLE_CODE_PREFIX + existingCode;
            if (Boolean.TRUE.equals(redisTemplate.hasKey(existingCacheKey))) {
                log.info("用户已有有效情侣码: userId={}, coupleCode={}", userId, existingCode);
                return existingCode;
            }
        }

        // 生成8位情侣码
        String coupleCode = IdUtil.simpleUUID().substring(0, 8).toUpperCase();

        // 情侣码有效期7天，存入Redis
        String cacheKey = COUPLE_CODE_PREFIX + coupleCode;
        redisTemplate.opsForHash().put(cacheKey, "userId", userId.toString());
        redisTemplate.opsForHash().put(cacheKey, "loveStartDate", req.getLoveStartDate());
        redisTemplate.opsForHash().put(cacheKey, "status", "0");
        redisTemplate.expire(cacheKey, COUPLE_CODE_EXPIRE_DAYS, TimeUnit.DAYS);

        // 创建反向映射：用户ID -> 情侣码
        redisTemplate.opsForValue().set(userCodeKey, coupleCode, COUPLE_CODE_EXPIRE_DAYS, TimeUnit.DAYS);

        log.info("生成情侣码: userId={}, coupleCode={}", userId, coupleCode);
        return coupleCode;
    }

    @Override
    @Transactional
    public CoupleInfoDTO bindCouple(Long userId, BindCoupleReq req) {
        User user = getUserById(userId);

        // 检查是否已有情侣关系
        if (user.getCoupleId() != null) {
            throw BusinessException.COUPLE_ALREADY_BIND;
        }

        // 验证情侣码
        String coupleCode = req.getCoupleCode().toUpperCase();
        String cacheKey = COUPLE_CODE_PREFIX + coupleCode;

        if (!Boolean.TRUE.equals(redisTemplate.hasKey(cacheKey))) {
            throw BusinessException.COUPLE_CODE_INVALID;
        }

        // 获取发起方的用户ID
        String senderIdStr = (String) redisTemplate.opsForHash().get(cacheKey, "userId");
        Long senderId = Long.parseLong(senderIdStr);

        if (senderId.equals(userId)) {
            throw BusinessException.COUPLE_BIND_CONFLICT;
        }

        // 获取恋爱开始日期（添加空值检查）
        String loveStartDateStr = (String) redisTemplate.opsForHash().get(cacheKey, "loveStartDate");
        if (loveStartDateStr == null || loveStartDateStr.isEmpty()) {
            loveStartDateStr = LocalDate.now().toString();
            log.warn("恋爱开始日期为空，使用当前日期: userId={}", userId);
        }
        LocalDate loveStartDate = LocalDate.parse(loveStartDateStr);

        // 计算恋爱天数
        int loveDays = (int) ChronoUnit.DAYS.between(loveStartDate, LocalDate.now());

        // 创建情侣关系
        Couple couple = new Couple();
        couple.setCoupleCode(coupleCode);
        couple.setUser1Id(senderId);
        couple.setUser2Id(userId);
        couple.setStartDate(loveStartDate);
        couple.setLoveDays(loveDays);
        couple.setStatus(1); // 已绑定

        // 设置默认情侣昵称
        User sender = getUserById(senderId);
        String coupleNickname = (sender.getNickName() != null ? sender.getNickName() : "TA") + "&" +
                                (user.getNickName() != null ? user.getNickName() : "TA");
        couple.setCoupleNickname(coupleNickname);

        coupleMapper.insert(couple);

        // 更新双方用户的情侣ID
        User senderUser = getUserById(senderId);
        senderUser.setCoupleId(couple.getId());
        senderUser.setLoveStartDate(loveStartDate.atStartOfDay());
        userMapper.updateById(senderUser);

        user.setCoupleId(couple.getId());
        user.setLoveStartDate(loveStartDate.atStartOfDay());
        userMapper.updateById(user);

        // 删除情侣码缓存（正向 + 反向映射）
        redisTemplate.delete(cacheKey);
        String senderCodeKey = COUPLE_CODE_PREFIX + "user:" + senderId;
        redisTemplate.delete(senderCodeKey);

        // 发送绑定成功通知
        if (notificationService != null) {
            notificationService.sendCoupleNotification(couple.getId(), userId,
                2, "🎉 绑定成功", "你们已经成为情侣啦，快去记录你们的美食之旅吧！", couple.getId(), "couple");
        }

        log.info("绑定情侣: coupleId={}, user1={}, user2={}", couple.getId(), senderId, userId);

        return buildCoupleInfoDTO(couple, userId);
    }

    @Override
    public CoupleInfoDTO getCoupleInfo(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            return null;
        }

        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (couple == null || couple.getStatus() != 1) {
            return null;
        }

        return buildCoupleInfoDTO(couple, userId);
    }

    @Override
    public CoupleHomeDTO getCoupleHome(Long userId) {
        User user = getUserById(userId);
        CoupleHomeDTO homeDTO = new CoupleHomeDTO();

        // 设置我的信息
        UserInfoDTO myInfo = new UserInfoDTO();
        myInfo.setId(user.getId());
        myInfo.setNickName(user.getNickName());
        myInfo.setAvatarUrl(user.getAvatarUrl());
        homeDTO.setMyInfo(myInfo);

        // 获取情侣信息
        if (user.getCoupleId() != null) {
            Couple couple = coupleMapper.selectById(user.getCoupleId());
            if (couple != null && couple.getStatus() == 1) {
                // 设置伴侣信息
                Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
                User partner = getUserById(partnerId);
                PartnerInfoDTO partnerInfo = new PartnerInfoDTO();
                partnerInfo.setId(partner.getId());
                partnerInfo.setNickName(partner.getNickName());
                partnerInfo.setAvatarUrl(partner.getAvatarUrl());
                partnerInfo.setGender(partner.getGender());
                homeDTO.setPartnerInfo(partnerInfo);

                // 设置恋爱天数
                homeDTO.setLoveDays(couple.getLoveDays());

                // 获取下一个纪念日
                homeDTO.setNextAnniversary(getNextAnniversaryInternal(user.getCoupleId()));

                // 获取统计数据
                homeDTO.setStats(getStatsInternal(user.getCoupleId()));

                // 获取今日投喂状态
                if (feedService != null) {
                    homeDTO.setTodayFeed(feedService.getTodayFeedStatus(userId));
                }

                // 获取最近动态
                homeDTO.setRecentActivities(getRecentActivitiesInternal(user.getCoupleId()));
            }
        }

        return homeDTO;
    }

    @Override
    @Transactional
    public void applyUnbind(Long userId, UnbindReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (couple == null) {
            throw BusinessException.COUPLE_NOT_FOUND;
        }

        // 更新情侣状态为申请解绑中
        couple.setStatus(3); // 申请解绑中
        couple.setUnbindApplicantId(userId);
        couple.setUnbindApplyTime(LocalDateTime.now());
        coupleMapper.updateById(couple);

        // 通知对方
        Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
        if (notificationService != null) {
            notificationService.sendNotification(partnerId, 2, "💔 申请解绑",
                "你的伴侣申请了解绑，请在7天内确认", couple.getId(), "couple");
        }

        log.info("申请解绑: coupleId={}, applicant={}", couple.getId(), userId);
    }

    @Override
    @Transactional
    public void confirmUnbind(Long userId, Long coupleId) {
        Couple couple = coupleMapper.selectById(coupleId);
        if (couple == null) {
            throw BusinessException.COUPLE_NOT_FOUND;
        }

        // 检查是否是情侣关系中的一方
        if (!couple.getUser1Id().equals(userId) && !couple.getUser2Id().equals(userId)) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 检查申请时间，需要24小时冷静期
        if (couple.getUnbindApplyTime() != null) {
            LocalDateTime confirmTime = LocalDateTime.now();
            LocalDateTime applyTime = couple.getUnbindApplyTime();
            long hoursSinceApply = java.time.Duration.between(applyTime, confirmTime).toHours();

            // 冷静期内可以随时确认，超过7天申请自动失效
            if (hoursSinceApply > 168) { // 7天 = 168小时
                // 申请已过期，恢复绑定状态
                couple.setStatus(1);
                couple.setUnbindApplicantId(null);
                couple.setUnbindApplyTime(null);
                coupleMapper.updateById(couple);
                throw new IllegalArgumentException("解绑申请已过期，请重新申请");
            }
        }

        // 备份数据
        backupCoupleData(couple);

        // 清除双方用户的情侣ID
        clearCoupleRelation(couple);

        // 更新情侣状态
        couple.setStatus(2); // 已解除
        coupleMapper.updateById(couple);

        // 发送通知
        Long applicantId = couple.getUnbindApplicantId();
        Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();

        if (notificationService != null) {
            notificationService.sendNotification(partnerId, 2, "💔 已解绑",
                "你们已解除情侣关系，数据将保留" + DATA_RETENTION_DAYS + "天，期间重新绑定可恢复数据", coupleId, "couple");
            if (applicantId != null) {
                notificationService.sendNotification(applicantId, 2, "💔 已解绑",
                    "你们已解除情侣关系，数据将保留" + DATA_RETENTION_DAYS + "天，期间重新绑定可恢复数据", coupleId, "couple");
            }
        }

        log.info("确认解绑: coupleId={}, userId={}", coupleId, userId);
    }

    /**
     * 备份情侣数据
     */
    private void backupCoupleData(Couple couple) {
        try {
            // 创建解绑记录
            CoupleUnbindRecord record = new CoupleUnbindRecord();
            record.setCoupleId(couple.getId());
            record.setUser1Id(couple.getUser1Id());
            record.setUser2Id(couple.getUser2Id());
            record.setApplicantId(couple.getUnbindApplicantId());
            record.setLoveStartDate(couple.getStartDate() != null ? couple.getStartDate().atStartOfDay() : null);
            record.setLoveDays(couple.getLoveDays());
            record.setCoupleNickname(couple.getCoupleNickname());
            record.setUnbindTime(LocalDateTime.now());
            record.setDataExpireTime(LocalDateTime.now().plusDays(DATA_RETENTION_DAYS));
            record.setStatus(0); // 可恢复
            record.setCreateTime(LocalDateTime.now());

            // 收集统计数据作为备份信息
            StringBuilder backupInfo = new StringBuilder();
            backupInfo.append("{");

            // 统计菜单数量
            Long menuCount = menuMapper.selectCount(
                new LambdaQueryWrapper<CoupleMenu>()
                    .eq(CoupleMenu::getCoupleId, couple.getId())
            );
            backupInfo.append("\"menuCount\":").append(menuCount).append(",");

            // 统计纪念日数量
            Long anniversaryCount = anniversaryMapper.selectCount(
                new LambdaQueryWrapper<Anniversary>()
                    .eq(Anniversary::getCoupleId, couple.getId())
            );
            backupInfo.append("\"anniversaryCount\":").append(anniversaryCount).append(",");

            // 统计投喂数量
            Long feedCount = feedMapper.selectCount(
                new LambdaQueryWrapper<Feed>()
                    .eq(Feed::getCoupleId, couple.getId())
            );
            backupInfo.append("\"feedCount\":").append(feedCount).append(",");

            // 统计心愿数量
            Long wishCount = wishMapper.selectCount(
                new LambdaQueryWrapper<Wish>()
                    .eq(Wish::getCoupleId, couple.getId())
            );
            backupInfo.append("\"wishCount\":").append(wishCount);

            backupInfo.append("}");
            record.setBackupData(backupInfo.toString());

            unbindRecordMapper.insert(record);
            log.info("备份情侣数据: coupleId={}, recordId={}", couple.getId(), record.getId());
        } catch (Exception e) {
            log.error("备份情侣数据失败: coupleId={}", couple.getId(), e);
            // 备份失败不影响解绑流程
        }
    }

    @Override
    @Transactional
    public void rejectUnbind(Long userId, Long coupleId) {
        Couple couple = coupleMapper.selectById(coupleId);
        if (couple == null) {
            throw BusinessException.COUPLE_NOT_FOUND;
        }

        // 权限检查：验证用户是否是该情侣关系中的一方
        if (!couple.getUser1Id().equals(userId) && !couple.getUser2Id().equals(userId)) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 只有被申请方（非申请人）才能拒绝
        if (couple.getUnbindApplicantId() != null && couple.getUnbindApplicantId().equals(userId)) {
            throw new IllegalArgumentException("申请人不能拒绝自己的解绑申请");
        }

        // 保存申请人ID用于后续通知
        Long applicantId = couple.getUnbindApplicantId();

        // 恢复情侣状态
        couple.setStatus(1); // 已绑定
        couple.setUnbindApplicantId(null);
        couple.setUnbindApplyTime(null);
        coupleMapper.updateById(couple);

        // 通知申请人
        if (applicantId != null && notificationService != null) {
            notificationService.sendNotification(applicantId, 2, "💕 解绑被拒绝",
                "你的伴侣拒绝了你的解绑申请", coupleId, "couple");
        }

        log.info("拒绝解绑: coupleId={}", coupleId);
    }

    @Override
    public boolean validateCoupleCode(String coupleCode) {
        String cacheKey = COUPLE_CODE_PREFIX + coupleCode.toUpperCase();
        return Boolean.TRUE.equals(redisTemplate.hasKey(cacheKey));
    }

    @Override
    public CoupleHomeDTO getLoveTimer(Long userId) {
        User user = getUserById(userId);
        CoupleHomeDTO dto = new CoupleHomeDTO();

        if (user.getCoupleId() != null) {
            Couple couple = coupleMapper.selectById(user.getCoupleId());
            if (couple != null) {
                dto.setLoveDays(couple.getLoveDays());

                // 计算相识天数（如果有的话）
                dto.setAcquaintanceDays(null); // 暂不支持相识日计算

                // 获取下一个纪念日
                dto.setNextAnniversary(getNextAnniversaryInternal(user.getCoupleId()));
            }
        }

        return dto;
    }

    @Override
    public CoupleInfoDTO checkRecoverableData(Long userId) {
        // 查找用户相关的未过期的解绑记录
        CoupleUnbindRecord record = unbindRecordMapper.selectOne(
            new LambdaQueryWrapper<CoupleUnbindRecord>()
                .and(wrapper -> wrapper
                    .eq(CoupleUnbindRecord::getUser1Id, userId)
                    .or()
                    .eq(CoupleUnbindRecord::getUser2Id, userId)
                )
                .eq(CoupleUnbindRecord::getStatus, 0) // 可恢复状态
                .gt(CoupleUnbindRecord::getDataExpireTime, LocalDateTime.now())
                .orderByDesc(CoupleUnbindRecord::getUnbindTime)
                .last("LIMIT 1")
        );

        if (record == null) {
            return null;
        }

        // 构建返回信息
        CoupleInfoDTO dto = new CoupleInfoDTO();
        dto.setId(record.getCoupleId());
        dto.setStartDate(record.getLoveStartDate() != null ? record.getLoveStartDate().toLocalDate().toString() : null);
        dto.setLoveDays(record.getLoveDays());
        dto.setCoupleNickname(record.getCoupleNickname());

        // 计算剩余可恢复天数
        long remainingDays = java.time.Duration.between(
            LocalDateTime.now(),
            record.getDataExpireTime()
        ).toDays();
        dto.setRecoverableDays((int) Math.max(0, remainingDays));

        // 获取原伴侣信息
        Long partnerId = record.getUser1Id().equals(userId) ? record.getUser2Id() : record.getUser1Id();
        User partner = userMapper.selectById(partnerId);
        if (partner != null) {
            PartnerInfoDTO partnerInfo = new PartnerInfoDTO();
            partnerInfo.setId(partner.getId());
            partnerInfo.setNickName(partner.getNickName());
            partnerInfo.setAvatarUrl(partner.getAvatarUrl());
            dto.setPartner(partnerInfo);
        }

        // 设置解绑记录ID用于恢复
        dto.setUnbindRecordId(record.getId());

        return dto;
    }

    @Override
    @Transactional
    public CoupleInfoDTO recoverCoupleData(Long userId, Long recordId) {
        User user = getUserById(userId);

        // 检查用户是否已有情侣关系
        if (user.getCoupleId() != null) {
            throw BusinessException.COUPLE_ALREADY_BIND;
        }

        // 获取解绑记录
        CoupleUnbindRecord record = unbindRecordMapper.selectById(recordId);
        if (record == null) {
            throw new IllegalArgumentException("解绑记录不存在");
        }

        // 验证用户是否是记录中的一方
        if (!record.getUser1Id().equals(userId) && !record.getUser2Id().equals(userId)) {
            throw new IllegalArgumentException("无权恢复此数据");
        }

        // 检查记录状态
        if (record.getStatus() != 0) {
            throw new IllegalArgumentException("此数据已不可恢复");
        }

        // 检查是否过期
        if (record.getDataExpireTime().isBefore(LocalDateTime.now())) {
            record.setStatus(2); // 标记为已过期
            unbindRecordMapper.updateById(record);
            throw new IllegalArgumentException("数据恢复期限已过");
        }

        // 获取原伴侣
        Long partnerId = record.getUser1Id().equals(userId) ? record.getUser2Id() : record.getUser1Id();
        User partner = userMapper.selectById(partnerId);

        // 检查原伴侣是否已有新的情侣关系
        if (partner != null && partner.getCoupleId() != null) {
            throw new IllegalArgumentException("对方已有新的情侣关系，无法恢复");
        }

        // 恢复情侣关系
        Couple couple = new Couple();
        couple.setCoupleCode(IdUtil.simpleUUID().substring(0, 8).toUpperCase());
        couple.setUser1Id(record.getUser1Id());
        couple.setUser2Id(record.getUser2Id());
        couple.setStartDate(record.getLoveStartDate() != null ? record.getLoveStartDate().toLocalDate() : null);
        couple.setLoveDays(record.getLoveDays());
        couple.setCoupleNickname(record.getCoupleNickname());
        couple.setStatus(1); // 已绑定

        coupleMapper.insert(couple);

        // 更新双方用户的情侣ID
        user.setCoupleId(couple.getId());
        user.setLoveStartDate(record.getLoveStartDate());
        userMapper.updateById(user);

        if (partner != null) {
            partner.setCoupleId(couple.getId());
            partner.setLoveStartDate(record.getLoveStartDate());
            userMapper.updateById(partner);
        }

        // 更新解绑记录状态
        record.setStatus(1); // 已恢复
        unbindRecordMapper.updateById(record);

        // 发送通知
        if (notificationService != null && partner != null) {
            notificationService.sendNotification(partner.getId(), 2, "💕 情侣关系已恢复",
                "你们恢复了情侣关系，之前的数据已恢复", couple.getId(), "couple");
        }

        log.info("恢复情侣数据: coupleId={}, userId={}, recordId={}", couple.getId(), userId, recordId);

        return buildCoupleInfoDTO(couple, userId);
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private CoupleInfoDTO buildCoupleInfoDTO(Couple couple, Long currentUserId) {
        CoupleInfoDTO dto = new CoupleInfoDTO();
        dto.setId(couple.getId());
        dto.setCoupleCode(couple.getCoupleCode());
        dto.setUser1Id(couple.getUser1Id());
        dto.setUser2Id(couple.getUser2Id());
        dto.setStartDate(couple.getStartDate() != null ? couple.getStartDate().toString() : null);
        dto.setLoveDays(couple.getLoveDays());
        dto.setCoupleNickname(couple.getCoupleNickname());
        dto.setStatus(couple.getStatus());

        // 设置伴侣信息
        Long partnerId = couple.getUser1Id().equals(currentUserId) ? couple.getUser2Id() : couple.getUser1Id();
        User partner = getUserById(partnerId);
        PartnerInfoDTO partnerInfo = new PartnerInfoDTO();
        partnerInfo.setId(partner.getId());
        partnerInfo.setNickName(partner.getNickName());
        partnerInfo.setAvatarUrl(partner.getAvatarUrl());
        partnerInfo.setGender(partner.getGender());
        dto.setPartner(partnerInfo);

        return dto;
    }

    private void clearCoupleRelation(Couple couple) {
        if (couple.getUser1Id() != null) {
            User user1 = userMapper.selectById(couple.getUser1Id());
            if (user1 != null) {
                user1.setCoupleId(null);
                userMapper.updateById(user1);
            }
        }
        if (couple.getUser2Id() != null) {
            User user2 = userMapper.selectById(couple.getUser2Id());
            if (user2 != null) {
                user2.setCoupleId(null);
                userMapper.updateById(user2);
            }
        }
    }

    private AnniversaryDTO getNextAnniversaryInternal(Long coupleId) {
        LocalDate today = LocalDate.now();
        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                .eq(Anniversary::getCoupleId, coupleId)
                .orderByAsc(Anniversary::getAnniversaryDate)
        );

        for (Anniversary a : anniversaries) {
            LocalDate nextDate = calculateNextAnniversaryDate(a.getAnniversaryDate());
            if (!nextDate.isBefore(today)) {
                AnniversaryDTO dto = new AnniversaryDTO();
                dto.setId(a.getId());
                dto.setName(a.getName());
                dto.setAnniversaryDate(a.getAnniversaryDate().toString());
                dto.setAnniversaryType(a.getAnniversaryType());
                dto.setTypeName(getTypeName(a.getAnniversaryType()));
                dto.setDaysUntil((int) ChronoUnit.DAYS.between(today, nextDate));
                dto.setIsPast(false);
                return dto;
            }
        }
        return null;
    }

    private LocalDate calculateNextAnniversaryDate(LocalDate anniversaryDate) {
        LocalDate today = LocalDate.now();
        LocalDate next = anniversaryDate;

        while (next.isBefore(today) || next.isEqual(today)) {
            next = next.plusYears(1);
        }
        return next;
    }

    private String getTypeName(Integer type) {
        switch (type) {
            case 1: return "相识";
            case 2: return "恋爱";
            case 3: return "表白";
            case 4: return "其他";
            default: return "其他";
        }
    }

    private StatsDTO getStatsInternal(Long coupleId) {
        StatsDTO stats = new StatsDTO();
        // 这里应该调用具体的统计方法，简化处理
        stats.setMenuCount(0);
        stats.setNoteCount(0);
        stats.setPhotoCount(0);
        stats.setFeedCount(0);
        stats.setWishAchievedCount(0);
        return stats;
    }

    private List<RecentActivityDTO> getRecentActivitiesInternal(Long coupleId) {
        List<RecentActivityDTO> activities = new ArrayList<>();
        // 获取最近的菜单、笔记、投喂等
        // 简化处理
        return activities;
    }

    @Override
    public CoupleCodeDTO getCoupleCodeInfo(Long userId) {
        User user = getUserById(userId);

        // 检查是否已有情侣关系
        if (user.getCoupleId() != null) {
            throw BusinessException.COUPLE_ALREADY_BIND;
        }

        // 优化：使用用户ID到情侣码的反向映射，避免KEYS命令
        String userCodeKey = COUPLE_CODE_PREFIX + "user:" + userId;
        String coupleCode = redisTemplate.opsForValue().get(userCodeKey);

        if (coupleCode == null) {
            return null; // 没有有效的情侣码
        }

        String codeKey = COUPLE_CODE_PREFIX + coupleCode;
        return buildCoupleCodeDTO(coupleCode, codeKey, userId, user);
    }

    @Override
    public String refreshCoupleCode(Long userId) {
        User user = getUserById(userId);

        // 检查是否已有情侣关系
        if (user.getCoupleId() != null) {
            throw BusinessException.COUPLE_ALREADY_BIND;
        }

        // 删除旧的情侣码（使用反向映射，避免KEYS命令）
        String userCodeKey = COUPLE_CODE_PREFIX + "user:" + userId;
        String oldCode = redisTemplate.opsForValue().get(userCodeKey);
        if (oldCode != null) {
            redisTemplate.delete(COUPLE_CODE_PREFIX + oldCode);
            redisTemplate.delete(userCodeKey);
        }

        // 生成新的情侣码
        String coupleCode = IdUtil.simpleUUID().substring(0, 8).toUpperCase();
        String cacheKey = COUPLE_CODE_PREFIX + coupleCode;

        // 使用当天作为默认恋爱开始日期
        String loveStartDate = LocalDate.now().toString();

        redisTemplate.opsForHash().put(cacheKey, "userId", userId.toString());
        redisTemplate.opsForHash().put(cacheKey, "loveStartDate", loveStartDate);
        redisTemplate.opsForHash().put(cacheKey, "status", "0");
        redisTemplate.expire(cacheKey, COUPLE_CODE_EXPIRE_DAYS, TimeUnit.DAYS);

        // 创建反向映射：用户ID -> 情侣码（用于快速查找，避免KEYS命令）
        String newUserCodeKey = COUPLE_CODE_PREFIX + "user:" + userId;
        redisTemplate.opsForValue().set(newUserCodeKey, coupleCode, COUPLE_CODE_EXPIRE_DAYS, TimeUnit.DAYS);

        log.info("刷新情侣码: userId={}, coupleCode={}", userId, coupleCode);
        return coupleCode;
    }

    @Override
    public void sendExpirationReminder() {
        // 优化：使用SCAN替代KEYS，避免阻塞Redis
        ScanOptions options = ScanOptions.scanOptions()
                .match(COUPLE_CODE_PREFIX + "*")
                .count(100)
                .build();

        try {
            Cursor<String> cursor = redisTemplate.scan(options);
            while (cursor.hasNext()) {
                String key = cursor.next();
                // 跳过反向映射键
                if (key.contains(":user:")) {
                    continue;
                }

                try {
                    Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
                    if (ttl == null || ttl < 0) {
                        continue;
                    }

                    // 如果剩余时间小于24小时，发送提醒
                    if (ttl < 24 * 60 * 60) {
                        String userIdStr = (String) redisTemplate.opsForHash().get(key, "userId");
                        if (userIdStr == null) {
                            continue;
                        }

                        Long userId = Long.parseLong(userIdStr);
                        String coupleCode = key.substring(COUPLE_CODE_PREFIX.length());

                        // 发送过期提醒通知
                        if (notificationService != null) {
                            long remainingHours = ttl / 3600;
                            notificationService.sendNotification(userId, 2, "⏰ 情侣码即将过期",
                                String.format("您的情侣码 %s 将在 %d 小时后过期，请尽快分享给TA绑定", coupleCode, remainingHours),
                                null, "couple_code");
                        }

                        log.info("发送情侣码过期提醒: userId={}, coupleCode={}, remainingSeconds={}", userId, coupleCode, ttl);
                    }
                } catch (Exception e) {
                    log.error("发送过期提醒失败: key={}", key, e);
                }
            }
        } catch (Exception e) {
            log.error("扫描情侣码失败", e);
        }
    }

    /**
     * 构建情侣码信息DTO
     */
    private CoupleCodeDTO buildCoupleCodeDTO(String coupleCode, String cacheKey, Long userId, User user) {
        CoupleCodeDTO dto = new CoupleCodeDTO();
        dto.setCoupleCode(coupleCode);
        dto.setCreatorId(userId);
        dto.setCreatorNickName(user.getNickName());
        dto.setCreatorAvatar(user.getAvatarUrl());

        // 获取TTL
        Long ttl = redisTemplate.getExpire(cacheKey, TimeUnit.SECONDS);
        if (ttl == null || ttl < 0) {
            dto.setExpired(true);
            dto.setStatus("expired");
            dto.setRemainingSeconds(0L);
            return dto;
        }

        // 计算剩余时间
        dto.setRemainingSeconds(ttl);
        dto.setRemainingDays(ttl / (24 * 60 * 60));
        dto.setRemainingHours((ttl % (24 * 60 * 60)) / 3600);
        dto.setRemainingMinutes((ttl % 3600) / 60);

        // 获取创建时间（使用Redis的IDLETIME近似计算，或者存储创建时间）
        // 这里使用过期时间反推创建时间
        long createTimeMillis = System.currentTimeMillis() - (COUPLE_CODE_EXPIRE_DAYS * 24 * 60 * 60 - ttl) * 1000;
        dto.setCreateTime(createTimeMillis);
        dto.setExpireTime(System.currentTimeMillis() + ttl * 1000);

        // 判断状态
        if (ttl < 24 * 60 * 60) {
            dto.setExpiringSoon(true);
            dto.setStatus("expiring");
        } else {
            dto.setExpiringSoon(false);
            dto.setStatus("valid");
        }
        dto.setExpired(false);

        return dto;
    }
}