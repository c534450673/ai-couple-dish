package com.aicoupledish.service;

import com.aicoupledish.domain.dto.InviteCodeDTO;
import com.aicoupledish.domain.dto.InviteStatsDTO;
import com.aicoupledish.domain.dto.ReferralDTO;

import java.util.List;

/**
 * 邀请服务接口
 */
public interface InviteService {

    /**
     * 获取或创建用户邀请码
     */
    InviteCodeDTO getOrCreateInviteCode(Long userId);

    /**
     * 使用邀请码注册
     */
    void useInviteCode(Long userId, String inviteCode);

    /**
     * 获取邀请记录列表
     */
    List<ReferralDTO> getReferralList(Long userId, Integer limit);

    /**
     * 获取邀请统计
     */
    InviteStatsDTO getInviteStats(Long userId);

    /**
     * 处理绑定情侣奖励
     */
    void processBindCoupleReward(Long userId);

    /**
     * 获取邀请排行榜
     */
    List<InviteStatsDTO.InviteRankItem> getInviteRankList(Integer limit);

    /**
     * 验证邀请码
     */
    boolean validateInviteCode(String inviteCode);

    /**
     * 获取邀请码详情（公开信息）
     */
    InviteCodeDTO getInviteCodeInfo(String inviteCode);
}
