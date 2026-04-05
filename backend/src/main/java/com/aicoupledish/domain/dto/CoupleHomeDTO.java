package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 情侣主页DTO
 */
@Data
public class CoupleHomeDTO {

    /**
     * 我的信息
     */
    private UserInfoDTO myInfo;

    /**
     * 伴侣信息
     */
    private PartnerInfoDTO partnerInfo;

    /**
     * 恋爱天数
     */
    private Integer loveDays;

    /**
     * 相识天数
     */
    private Integer acquaintanceDays;

    /**
     * 下一个纪念日
     */
    private AnniversaryDTO nextAnniversary;

    /**
     * 统计数据
     */
    private StatsDTO stats;

    /**
     * 今日投喂状态
     */
    private TodayFeedDTO todayFeed;

    /**
     * 最近动态
     */
    private java.util.List<RecentActivityDTO> recentActivities;
}