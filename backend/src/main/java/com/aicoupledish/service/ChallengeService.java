package com.aicoupledish.service;

import com.aicoupledish.domain.dto.ChallengeDTO;
import com.aicoupledish.domain.dto.CheckinRecordDTO;
import com.aicoupledish.domain.req.CheckinReq;
import com.aicoupledish.domain.req.CreateChallengeReq;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.util.List;

/**
 * 打卡挑战服务
 */
public interface ChallengeService {

    /**
     * 创建挑战
     *
     * @param userId 用户ID
     * @param req    创建请求
     * @return 挑战ID
     */
    Long createChallenge(Long userId, CreateChallengeReq req);

    /**
     * 接受挑战
     *
     * @param userId     用户ID
     * @param challengeId 挑战ID
     */
    void acceptChallenge(Long userId, Long challengeId);

    /**
     * 拒绝挑战
     *
     * @param userId     用户ID
     * @param challengeId 挑战ID
     */
    void rejectChallenge(Long userId, Long challengeId);

    /**
     * 取消挑战
     *
     * @param userId     用户ID
     * @param challengeId 挑战ID
     */
    void cancelChallenge(Long userId, Long challengeId);

    /**
     * 打卡
     *
     * @param userId 用户ID
     * @param req    打卡请求
     * @return 打卡记录DTO
     */
    CheckinRecordDTO checkin(Long userId, CheckinReq req);

    /**
     * 获取挑战详情
     *
     * @param userId     用户ID
     * @param challengeId 挑战ID
     * @return 挑战详情
     */
    ChallengeDTO getChallengeDetail(Long userId, Long challengeId);

    /**
     * 获取挑战列表
     *
     * @param userId 用户ID
     * @param status 状态（可选）
     * @return 挑战列表
     */
    List<ChallengeDTO> getChallengeList(Long userId, Integer status);

    /**
     * 分页获取打卡记录
     *
     * @param userId      用户ID
     * @param challengeId 挑战ID
     * @param pageNum     页码
     * @param pageSize    每页大小
     * @return 打卡记录分页
     */
    Page<CheckinRecordDTO> getCheckinRecords(Long userId, Long challengeId, Integer pageNum, Integer pageSize);

    /**
     * 获取待处理的挑战列表（伙伴发来的邀请）
     *
     * @param userId 用户ID
     * @return 挑战列表
     */
    List<ChallengeDTO> getPendingChallenges(Long userId);

    /**
     * 检查并更新挑战状态
     */
    void checkAndUpdateChallengeStatus();
}
