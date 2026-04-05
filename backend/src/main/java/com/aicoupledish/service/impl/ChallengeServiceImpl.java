package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.ChallengeMapper;
import com.aicoupledish.dao.mapper.CheckinRecordMapper;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Challenge;
import com.aicoupledish.dao.model.CheckinRecord;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.ChallengeDTO;
import com.aicoupledish.domain.dto.CheckinRecordDTO;
import com.aicoupledish.domain.req.CheckinReq;
import com.aicoupledish.domain.req.CreateChallengeReq;
import com.aicoupledish.service.ChallengeService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 打卡挑战服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChallengeServiceImpl implements ChallengeService {

    private final ChallengeMapper challengeMapper;
    private final CheckinRecordMapper checkinRecordMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    /**
     * 挑战状态
     */
    private static final int STATUS_IN_PROGRESS = 0;
    private static final int STATUS_COMPLETED = 1;
    private static final int STATUS_FAILED = 2;
    private static final int STATUS_CANCELLED = 3;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createChallenge(Long userId, CreateChallengeReq req) {
        // 获取情侣信息
        Couple couple = getCoupleByUserId(userId);
        Long partnerId = getPartnerId(couple, userId);

        // 创建挑战
        Challenge challenge = new Challenge();
        challenge.setCoupleId(couple.getId());
        challenge.setCreatorId(userId);
        challenge.setPartnerId(partnerId);
        challenge.setChallengeType(req.getChallengeType());
        challenge.setTitle(req.getTitle());
        challenge.setDescription(req.getDescription());
        challenge.setTargetDays(req.getTargetDays());
        challenge.setCurrentDays(0);
        challenge.setStatus(STATUS_IN_PROGRESS);
        challenge.setStartDate(req.getStartDate() != null ? req.getStartDate() : LocalDate.now());
        challenge.setReward(req.getReward());
        challenge.setIsDeleted(0);

        challengeMapper.insert(challenge);

        log.info("用户 {} 创建挑战成功, challengeId={}", userId, challenge.getId());
        return challenge.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void acceptChallenge(Long userId, Long challengeId) {
        Challenge challenge = getChallengeById(challengeId);
        validateChallengePartner(challenge, userId);

        if (challenge.getStatus() != STATUS_IN_PROGRESS) {
            throw new BusinessException("挑战状态不允许操作");
        }

        // 接受挑战后状态不变，只是确认参与
        log.info("用户 {} 接受挑战 {}", userId, challengeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void rejectChallenge(Long userId, Long challengeId) {
        Challenge challenge = getChallengeById(challengeId);
        validateChallengePartner(challenge, userId);

        if (challenge.getStatus() != STATUS_IN_PROGRESS) {
            throw new BusinessException("挑战状态不允许操作");
        }

        challenge.setStatus(STATUS_CANCELLED);
        challengeMapper.updateById(challenge);

        log.info("用户 {} 拒绝挑战 {}", userId, challengeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void cancelChallenge(Long userId, Long challengeId) {
        Challenge challenge = getChallengeById(challengeId);

        // 只有创建者可以取消
        if (!challenge.getCreatorId().equals(userId)) {
            throw new BusinessException("只有创建者可以取消挑战");
        }

        if (challenge.getStatus() != STATUS_IN_PROGRESS) {
            throw new BusinessException("挑战状态不允许取消");
        }

        challenge.setStatus(STATUS_CANCELLED);
        challengeMapper.updateById(challenge);

        log.info("用户 {} 取消挑战 {}", userId, challengeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CheckinRecordDTO checkin(Long userId, CheckinReq req) {
        Challenge challenge = getChallengeById(req.getChallengeId());

        // 验证是否是挑战参与者
        if (!challenge.getCreatorId().equals(userId) && !challenge.getPartnerId().equals(userId)) {
            throw new BusinessException("您不是该挑战的参与者");
        }

        if (challenge.getStatus() != STATUS_IN_PROGRESS) {
            throw new BusinessException("挑战已结束");
        }

        LocalDate today = LocalDate.now();

        // 检查今天是否已打卡
        Long todayCheckinCount = checkinRecordMapper.selectCount(
                new LambdaQueryWrapper<CheckinRecord>()
                        .eq(CheckinRecord::getChallengeId, challenge.getId())
                        .eq(CheckinRecord::getUserId, userId)
                        .eq(CheckinRecord::getCheckinDate, today)
        );
        if (todayCheckinCount > 0) {
            throw new BusinessException("今日已打卡");
        }

        // 创建打卡记录
        CheckinRecord record = new CheckinRecord();
        record.setChallengeId(challenge.getId());
        record.setUserId(userId);
        record.setCheckinDate(today);
        record.setContent(req.getContent());
        record.setImageUrl(req.getImageUrl());

        checkinRecordMapper.insert(record);

        // 更新挑战当前天数
        // 统计两人总共打卡的不同日期数
        List<CheckinRecord> allRecords = checkinRecordMapper.selectList(
                new LambdaQueryWrapper<CheckinRecord>()
                        .eq(CheckinRecord::getChallengeId, challenge.getId())
                        .select(CheckinRecord::getCheckinDate)
        );
        Set<LocalDate> uniqueDates = allRecords.stream()
                .map(CheckinRecord::getCheckinDate)
                .collect(Collectors.toSet());

        challenge.setCurrentDays(uniqueDates.size());

        // 检查是否完成
        if (challenge.getCurrentDays() >= challenge.getTargetDays()) {
            challenge.setStatus(STATUS_COMPLETED);
            challenge.setEndDate(today);
        }

        challengeMapper.updateById(challenge);

        log.info("用户 {} 完成打卡, challengeId={}, 当前进度 {}/{}", userId, challenge.getId(), challenge.getCurrentDays(), challenge.getTargetDays());

        return convertToCheckinRecordDTO(record);
    }

    @Override
    public ChallengeDTO getChallengeDetail(Long userId, Long challengeId) {
        Challenge challenge = getChallengeById(challengeId);

        // 验证权限
        Couple couple = getCoupleByUserId(userId);
        if (!challenge.getCoupleId().equals(couple.getId())) {
            throw new BusinessException("无权查看该挑战");
        }

        ChallengeDTO dto = convertToChallengeDTO(challenge);

        // 检查今日是否已打卡
        LocalDate today = LocalDate.now();
        Long todayCheckin = checkinRecordMapper.selectCount(
                new LambdaQueryWrapper<CheckinRecord>()
                        .eq(CheckinRecord::getChallengeId, challengeId)
                        .eq(CheckinRecord::getUserId, userId)
                        .eq(CheckinRecord::getCheckinDate, today)
        );
        dto.setTodayChecked(todayCheckin > 0);

        // 计算进度百分比
        if (challenge.getTargetDays() != null && challenge.getTargetDays() > 0) {
            int percent = (int) ((challenge.getCurrentDays() * 100.0) / challenge.getTargetDays());
            dto.setProgressPercent(Math.min(percent, 100));
        }

        // 获取打卡记录
        List<CheckinRecord> records = checkinRecordMapper.selectList(
                new LambdaQueryWrapper<CheckinRecord>()
                        .eq(CheckinRecord::getChallengeId, challengeId)
                        .orderByDesc(CheckinRecord::getCheckinDate)
                        .last("LIMIT 20")
        );

        // 批量加载用户信息（修复N+1查询）
        Set<Long> userIds = records.stream()
                .map(CheckinRecord::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = userIds.isEmpty() ? Collections.emptyMap() : getUserMap(new ArrayList<>(userIds));

        dto.setCheckinRecords(records.stream()
                .map(record -> convertToCheckinRecordDTOWithCache(record, userMap))
                .collect(Collectors.toList()));

        return dto;
    }

    @Override
    public List<ChallengeDTO> getChallengeList(Long userId, Integer status) {
        Couple couple = getCoupleByUserId(userId);

        LambdaQueryWrapper<Challenge> wrapper = new LambdaQueryWrapper<Challenge>()
                .eq(Challenge::getCoupleId, couple.getId())
                .eq(Challenge::getIsDeleted, 0)
                .orderByDesc(Challenge::getCreateTime);

        if (status != null) {
            wrapper.eq(Challenge::getStatus, status);
        }

        List<Challenge> challenges = challengeMapper.selectList(wrapper);
        return challenges.stream()
                .map(this::convertToChallengeDTO)
                .collect(Collectors.toList());
    }

    @Override
    public Page<CheckinRecordDTO> getCheckinRecords(Long userId, Long challengeId, Integer pageNum, Integer pageSize) {
        Challenge challenge = getChallengeById(challengeId);

        // 验证权限：只有挑战参与者才能查看打卡记录
        Couple couple = getCoupleByUserId(userId);
        if (!challenge.getCoupleId().equals(couple.getId())) {
            throw new BusinessException("无权查看该挑战的打卡记录");
        }

        Page<CheckinRecord> page = new Page<>(pageNum, pageSize);
        Page<CheckinRecord> result = checkinRecordMapper.selectPage(page,
                new LambdaQueryWrapper<CheckinRecord>()
                        .eq(CheckinRecord::getChallengeId, challengeId)
                        .orderByDesc(CheckinRecord::getCheckinDate));

        Page<CheckinRecordDTO> dtoPage = new Page<>();
        BeanUtils.copyProperties(result, dtoPage, "records");
        dtoPage.setRecords(result.getRecords().stream()
                .map(this::convertToCheckinRecordDTO)
                .collect(Collectors.toList()));

        return dtoPage;
    }

    @Override
    public List<ChallengeDTO> getPendingChallenges(Long userId) {
        Couple couple = getCoupleByUserId(userId);

        // 获取伙伴发来的挑战（自己是partnerId）
        List<Challenge> challenges = challengeMapper.selectList(
                new LambdaQueryWrapper<Challenge>()
                        .eq(Challenge::getCoupleId, couple.getId())
                        .eq(Challenge::getPartnerId, userId)
                        .eq(Challenge::getStatus, STATUS_IN_PROGRESS)
                        .eq(Challenge::getIsDeleted, 0)
                        .orderByDesc(Challenge::getCreateTime)
        );

        return challenges.stream()
                .map(this::convertToChallengeDTO)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void checkAndUpdateChallengeStatus() {
        LocalDate yesterday = LocalDate.now().minusDays(1);

        // 查找进行中的挑战
        List<Challenge> challenges = challengeMapper.selectList(
                new LambdaQueryWrapper<Challenge>()
                        .eq(Challenge::getStatus, STATUS_IN_PROGRESS)
                        .eq(Challenge::getIsDeleted, 0)
        );

        for (Challenge challenge : challenges) {
            // 检查是否连续两天未打卡（简化逻辑：实际应根据业务规则）
            // 这里可以添加更复杂的失败判断逻辑
            log.debug("检查挑战状态: challengeId={}", challenge.getId());
        }
    }

    /**
     * 根据ID获取挑战
     */
    private Challenge getChallengeById(Long challengeId) {
        Challenge challenge = challengeMapper.selectById(challengeId);
        if (challenge == null) {
            throw new BusinessException("挑战不存在");
        }
        return challenge;
    }

    /**
     * 获取用户的情侣信息
     */
    private Couple getCoupleByUserId(Long userId) {
        List<Couple> couples = coupleMapper.selectList(
                new LambdaQueryWrapper<Couple>()
                        .eq(Couple::getStatus, 1)
                        .and(wrapper -> wrapper
                                .eq(Couple::getUser1Id, userId)
                                .or()
                                .eq(Couple::getUser2Id, userId))
                        .last("LIMIT 1")
        );
        if (couples.isEmpty()) {
            throw new BusinessException("您还没有绑定情侣");
        }
        return couples.get(0);
    }

    /**
     * 获取伙伴ID
     */
    private Long getPartnerId(Couple couple, Long userId) {
        return couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
    }

    /**
     * 验证是否是挑战伙伴
     */
    private void validateChallengePartner(Challenge challenge, Long userId) {
        if (!challenge.getPartnerId().equals(userId)) {
            throw new BusinessException("您不是该挑战的伙伴");
        }
    }

    /**
     * 转换为DTO
     */
    private ChallengeDTO convertToChallengeDTO(Challenge challenge) {
        ChallengeDTO dto = new ChallengeDTO();
        BeanUtils.copyProperties(challenge, dto);

        // 状态描述
        dto.setStatusDesc(getStatusDesc(challenge.getStatus()));

        // 获取用户信息
        Map<Long, User> userMap = getUserMap(Arrays.asList(challenge.getCreatorId(), challenge.getPartnerId()));
        User creator = userMap.get(challenge.getCreatorId());
        User partner = userMap.get(challenge.getPartnerId());

        if (creator != null) {
            dto.setCreatorName(creator.getNickName());
        }
        if (partner != null) {
            dto.setPartnerName(partner.getNickName());
        }

        return dto;
    }

    /**
     * 转换为打卡记录DTO
     */
    private CheckinRecordDTO convertToCheckinRecordDTO(CheckinRecord record) {
        return convertToCheckinRecordDTOWithCache(record, null);
    }

    /**
     * 转换为打卡记录DTO（使用缓存的用户数据，避免N+1查询）
     */
    private CheckinRecordDTO convertToCheckinRecordDTOWithCache(CheckinRecord record, Map<Long, User> userMap) {
        CheckinRecordDTO dto = new CheckinRecordDTO();
        BeanUtils.copyProperties(record, dto);

        // 获取用户信息（使用缓存或单独查询）
        User user = userMap != null ? userMap.get(record.getUserId()) : userMapper.selectById(record.getUserId());
        if (user != null) {
            dto.setUserName(user.getNickName());
            dto.setUserAvatar(user.getAvatarUrl());
        }

        return dto;
    }

    /**
     * 获取状态描述
     */
    private String getStatusDesc(Integer status) {
        switch (status) {
            case 0:
                return "进行中";
            case 1:
                return "已完成";
            case 2:
                return "已失败";
            case 3:
                return "已取消";
            default:
                return "未知";
        }
    }

    /**
     * 批量获取用户信息
     */
    private Map<Long, User> getUserMap(List<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return Collections.emptyMap();
        }
        List<User> users = userMapper.selectBatchIds(userIds);
        return users.stream().collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));
    }
}
