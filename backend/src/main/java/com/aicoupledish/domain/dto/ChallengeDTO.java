package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 挑战DTO
 */
@Data
public class ChallengeDTO {

    /**
     * 挑战ID
     */
    private Long id;

    /**
     * 挑战类型
     */
    private String challengeType;

    /**
     * 挑战标题
     */
    private String title;

    /**
     * 挑战描述
     */
    private String description;

    /**
     * 目标天数
     */
    private Integer targetDays;

    /**
     * 当前天数
     */
    private Integer currentDays;

    /**
     * 状态：0-进行中 1-已完成 2-已失败 3-已取消
     */
    private Integer status;

    /**
     * 状态描述
     */
    private String statusDesc;

    /**
     * 开始日期
     */
    private LocalDate startDate;

    /**
     * 结束日期
     */
    private LocalDate endDate;

    /**
     * 奖励
     */
    private String reward;

    /**
     * 创建者ID
     */
    private Long creatorId;

    /**
     * 挑战伙伴ID
     */
    private Long partnerId;

    /**
     * 创建者名称
     */
    private String creatorName;

    /**
     * 伙伴名称
     */
    private String partnerName;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 打卡记录列表
     */
    private List<CheckinRecordDTO> checkinRecords;

    /**
     * 今日是否已打卡
     */
    private Boolean todayChecked;

    /**
     * 完成进度百分比
     */
    private Integer progressPercent;
}
