package com.aicoupledish.service.impl;

import cn.hutool.core.util.RandomUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.UserInviteCodeMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.mapper.UserReferralMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.dao.model.UserInviteCode;
import com.aicoupledish.dao.model.UserReferral;
import com.aicoupledish.domain.dto.InviteCodeDTO;
import com.aicoupledish.domain.dto.InviteStatsDTO;
import com.aicoupledish.domain.dto.ReferralDTO;
import com.aicoupledish.service.InviteService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 邀请服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InviteServiceImpl implements InviteService {

    private final UserInviteCodeMapper userInviteCodeMapper;
    private final UserReferralMapper userReferralMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;

    @Value("${invite.link-prefix:https://aicoupledish.com/invite/}")
    private String inviteLinkPrefix;

    @Value("${invite.register-reward:5.00}")
    private BigDecimal registerReward;

    @Value("${invite.bind-couple-reward:10.00}")
    private BigDecimal bindCoupleReward;

    @Override
    @Transactional
    public InviteCodeDTO getOrCreateInviteCode(Long userId) {
        User user = getUserById(userId);

        UserInviteCode inviteCode = userInviteCodeMapper.selectOne(
            new LambdaQueryWrapper<UserInviteCode>()
                .eq(UserInviteCode::getUserId, userId)
        );

        if (inviteCode == null) {
            inviteCode = new UserInviteCode();
            inviteCode.setUserId(userId);
            inviteCode.setInviteCode(generateUniqueCode());
            inviteCode.setInviteCount(0);
            inviteCode.setRewardAmount(BigDecimal.ZERO);
            userInviteCodeMapper.insert(inviteCode);
            log.info("创建邀请码: userId={}, code={}", userId, inviteCode.getInviteCode());
        }

        return buildInviteCodeDTO(inviteCode);
    }

    @Override
    @Transactional
    public void useInviteCode(Long userId, String inviteCode) {
        if (inviteCode == null || inviteCode.trim().isEmpty()) {
            return;
        }

        User user = getUserById(userId);

        // 检查是否已经使用过邀请码
        Long existCount = userReferralMapper.selectCount(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviteeId, userId)
        );

        if (existCount != null && existCount > 0) {
            log.info("用户已使用过邀请码: userId={}", userId);
            return;
        }

        // 查找邀请码
        UserInviteCode code = userInviteCodeMapper.selectOne(
            new LambdaQueryWrapper<UserInviteCode>()
                .eq(UserInviteCode::getInviteCode, inviteCode)
        );

        if (code == null) {
            log.warn("邀请码不存在: code={}", inviteCode);
            return;
        }

        // 不能邀请自己
        if (code.getUserId().equals(userId)) {
            log.warn("不能使用自己的邀请码: userId={}", userId);
            return;
        }

        // 创建邀请关系
        UserReferral referral = new UserReferral();
        referral.setInviterId(code.getUserId());
        referral.setInviteeId(userId);
        referral.setInviteCode(inviteCode);
        referral.setRegisterTime(LocalDateTime.now());
        referral.setRewardStatus(0);
        referral.setRewardAmount(registerReward);
        userReferralMapper.insert(referral);

        // 使用原子更新避免竞态条件
        userInviteCodeMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<UserInviteCode>()
                .eq(UserInviteCode::getId, code.getId())
                .setSql("invite_count = invite_count + 1"));

        log.info("使用邀请码成功: inviterId={}, inviteeId={}, code={}", code.getUserId(), userId, inviteCode);
    }

    @Override
    public List<ReferralDTO> getReferralList(Long userId, Integer limit) {
        List<UserReferral> referrals = userReferralMapper.selectList(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, userId)
                .orderByDesc(UserReferral::getRegisterTime)
                .last("LIMIT " + (limit != null ? limit : 50))
        );

        return referrals.stream().map(this::buildReferralDTO).collect(Collectors.toList());
    }

    @Override
    public InviteStatsDTO getInviteStats(Long userId) {
        InviteStatsDTO stats = new InviteStatsDTO();

        // 总邀请人数
        Long totalInvites = userReferralMapper.selectCount(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, userId)
        );
        stats.setTotalInvites(totalInvites != null ? totalInvites.intValue() : 0);

        // 已绑定情侣人数
        Long boundCoupleCount = userReferralMapper.selectCount(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, userId)
                .isNotNull(UserReferral::getBindCoupleTime)
        );
        stats.setBoundCoupleCount(boundCoupleCount != null ? boundCoupleCount.intValue() : 0);
        stats.setPendingBindCount(stats.getTotalInvites() - stats.getBoundCoupleCount());

        // 计算奖励金额
        BigDecimal totalReward = BigDecimal.ZERO;
        BigDecimal claimedReward = BigDecimal.ZERO;
        BigDecimal pendingReward = BigDecimal.ZERO;

        List<UserReferral> referrals = userReferralMapper.selectList(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, userId)
        );

        for (UserReferral referral : referrals) {
            if (referral.getRewardAmount() != null) {
                totalReward = totalReward.add(referral.getRewardAmount());
                if (referral.getRewardStatus() == 1) {
                    claimedReward = claimedReward.add(referral.getRewardAmount());
                } else {
                    pendingReward = pendingReward.add(referral.getRewardAmount());
                }
            }
        }

        stats.setTotalRewardAmount(totalReward);
        stats.setClaimedRewardAmount(claimedReward);
        stats.setPendingRewardAmount(pendingReward);

        // 本周新增
        LocalDateTime weekStart = LocalDate.now().minusDays(LocalDate.now().getDayOfWeek().getValue() - 1).atStartOfDay();
        Long weeklyNew = userReferralMapper.selectCount(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, userId)
                .ge(UserReferral::getRegisterTime, weekStart)
        );
        stats.setWeeklyNewInvites(weeklyNew != null ? weeklyNew.intValue() : 0);

        // 本月新增
        LocalDateTime monthStart = LocalDate.now().withDayOfMonth(1).atStartOfDay();
        Long monthlyNew = userReferralMapper.selectCount(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, userId)
                .ge(UserReferral::getRegisterTime, monthStart)
        );
        stats.setMonthlyNewInvites(monthlyNew != null ? monthlyNew.intValue() : 0);

        return stats;
    }

    @Override
    @Transactional
    public void processBindCoupleReward(Long userId) {
        // 查找邀请关系
        UserReferral referral = userReferralMapper.selectOne(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviteeId, userId)
                .isNull(UserReferral::getBindCoupleTime)
        );

        if (referral == null) {
            return;
        }

        // 检查是否已绑定情侣
        User user = userMapper.selectById(userId);
        if (user == null || user.getCoupleId() == null) {
            return;
        }

        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (couple == null || couple.getStatus() != 1) {
            return;
        }

        // 更新邀请关系
        referral.setBindCoupleTime(LocalDateTime.now());
        BigDecimal currentReward = referral.getRewardAmount() != null ? referral.getRewardAmount() : BigDecimal.ZERO;
        referral.setRewardAmount(currentReward.add(bindCoupleReward));
        userReferralMapper.updateById(referral);

        log.info("处理绑定情侣奖励: inviteeId={}, inviterId={}, reward={}",
            userId, referral.getInviterId(), bindCoupleReward);
    }

    @Override
    public List<InviteStatsDTO.InviteRankItem> getInviteRankList(Integer limit) {
        List<UserInviteCode> topInviters = userInviteCodeMapper.selectList(
            new LambdaQueryWrapper<UserInviteCode>()
                .orderByDesc(UserInviteCode::getInviteCount)
                .last("LIMIT " + (limit != null ? limit : 10))
        );

        List<InviteStatsDTO.InviteRankItem> rankList = new ArrayList<>();
        int rank = 1;
        for (UserInviteCode code : topInviters) {
            InviteStatsDTO.InviteRankItem item = new InviteStatsDTO.InviteRankItem();
            item.setRank(rank++);
            item.setUserId(code.getUserId());
            item.setInviteCount(code.getInviteCount());
            item.setRewardAmount(code.getRewardAmount());

            User user = userMapper.selectById(code.getUserId());
            if (user != null) {
                item.setUserName(user.getNickName());
                item.setUserAvatar(user.getAvatarUrl());
            }

            rankList.add(item);
        }

        return rankList;
    }

    @Override
    public boolean validateInviteCode(String inviteCode) {
        if (inviteCode == null || inviteCode.trim().isEmpty()) {
            return false;
        }

        Long count = userInviteCodeMapper.selectCount(
            new LambdaQueryWrapper<UserInviteCode>()
                .eq(UserInviteCode::getInviteCode, inviteCode)
        );

        return count != null && count > 0;
    }

    @Override
    public InviteCodeDTO getInviteCodeInfo(String inviteCode) {
        UserInviteCode code = userInviteCodeMapper.selectOne(
            new LambdaQueryWrapper<UserInviteCode>()
                .eq(UserInviteCode::getInviteCode, inviteCode)
        );

        if (code == null) {
            return null;
        }

        InviteCodeDTO dto = new InviteCodeDTO();
        dto.setInviteCode(code.getInviteCode());
        dto.setInviteCount(code.getInviteCount());
        dto.setRewardAmount(code.getRewardAmount());
        dto.setCreateTime(code.getCreateTime());

        User inviter = userMapper.selectById(code.getUserId());
        if (inviter != null) {
            // 可以返回部分邀请人信息
        }

        return dto;
    }

    /**
     * 生成唯一邀请码
     */
    private String generateUniqueCode() {
        String code;
        int attempts = 0;
        do {
            code = RandomUtil.randomString(6).toUpperCase();
            Long count = userInviteCodeMapper.selectCount(
                new LambdaQueryWrapper<UserInviteCode>()
                    .eq(UserInviteCode::getInviteCode, code)
            );
            if (count == null || count == 0) {
                return code;
            }
            attempts++;
        } while (attempts < 10);

        // 如果6位冲突，使用8位并确保唯一
        do {
            code = RandomUtil.randomString(8).toUpperCase();
            Long count = userInviteCodeMapper.selectCount(
                new LambdaQueryWrapper<UserInviteCode>()
                    .eq(UserInviteCode::getInviteCode, code)
            );
            if (count == null || count == 0) {
                return code;
            }
        } while (true);
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private InviteCodeDTO buildInviteCodeDTO(UserInviteCode code) {
        InviteCodeDTO dto = new InviteCodeDTO();
        dto.setId(code.getId());
        dto.setInviteCode(code.getInviteCode());
        dto.setInviteCount(code.getInviteCount());
        dto.setRewardAmount(code.getRewardAmount());
        dto.setCreateTime(code.getCreateTime());

        // 计算已绑定情侣的人数
        Long boundCount = userReferralMapper.selectCount(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, code.getUserId())
                .isNotNull(UserReferral::getBindCoupleTime)
        );
        dto.setBoundCount(boundCount != null ? boundCount.intValue() : 0);

        // 计算待发放奖励
        BigDecimal pendingReward = BigDecimal.ZERO;
        List<UserReferral> pendingReferrals = userReferralMapper.selectList(
            new LambdaQueryWrapper<UserReferral>()
                .eq(UserReferral::getInviterId, code.getUserId())
                .eq(UserReferral::getRewardStatus, 0)
        );
        for (UserReferral referral : pendingReferrals) {
            if (referral.getRewardAmount() != null) {
                pendingReward = pendingReward.add(referral.getRewardAmount());
            }
        }
        dto.setPendingRewardAmount(pendingReward);

        // 生成邀请链接和二维码
        dto.setInviteLink(inviteLinkPrefix + code.getInviteCode());
        dto.setQrcodeUrl("/qrcode/" + code.getInviteCode() + ".png");

        return dto;
    }

    private ReferralDTO buildReferralDTO(UserReferral referral) {
        ReferralDTO dto = new ReferralDTO();
        dto.setId(referral.getId());
        dto.setInviteeId(referral.getInviteeId());
        dto.setInviteCode(referral.getInviteCode());
        dto.setRegisterTime(referral.getRegisterTime());
        dto.setBindCoupleTime(referral.getBindCoupleTime());
        dto.setHasBoundCouple(referral.getBindCoupleTime() != null);
        dto.setRewardStatus(referral.getRewardStatus());
        dto.setRewardStatusName(referral.getRewardStatus() == 0 ? "待发放" : "已发放");
        dto.setRewardAmount(referral.getRewardAmount());
        dto.setRewardTime(referral.getRewardTime());

        User invitee = userMapper.selectById(referral.getInviteeId());
        if (invitee != null) {
            dto.setInviteeName(invitee.getNickName());
            dto.setInviteeAvatar(invitee.getAvatarUrl());
        }

        return dto;
    }
}
