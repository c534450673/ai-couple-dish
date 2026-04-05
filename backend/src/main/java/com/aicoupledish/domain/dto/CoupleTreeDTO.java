package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 情侣爱心树DTO
 */
@Data
public class CoupleTreeDTO {

    private Long id;

    /**
     * 等级
     */
    private Integer level;

    /**
     * 等级名称
     */
    private String levelName;

    /**
     * 总养分
     */
    private Long totalNutrient;

    /**
     * 当前等级养分
     */
    private Long currentLevelNutrient;

    /**
     * 升级所需养分
     */
    private Long nextLevelNutrient;

    /**
     * 升级进度百分比
     */
    private Integer progressPercent;

    /**
     * 皮肤ID
     */
    private String skinId;

    /**
     * 可用皮肤列表
     */
    private List<SkinInfo> availableSkins;

    /**
     * 今日获得养分
     */
    private Integer todayNutrient;

    /**
     * 养分变动日志
     */
    private List<NutrientLogInfo> nutrientLogs;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 皮肤信息
     */
    @Data
    public static class SkinInfo {
        private String skinId;
        private String skinName;
        private String previewUrl;
        private Integer requiredLevel;
        private Boolean unlocked;
    }

    /**
     * 养分日志信息
     */
    @Data
    public static class NutrientLogInfo {
        private Long id;
        private Long userId;
        private String userName;
        private String userAvatar;
        private Integer nutrientAmount;
        private String sourceAction;
        private String sourceActionName;
        private String remark;
        private LocalDateTime createTime;
    }
}
