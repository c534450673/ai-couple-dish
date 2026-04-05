package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 统计数据DTO
 */
@Data
public class StatsDTO {

    /**
     * 菜单数量
     */
    private Integer menuCount;

    /**
     * 笔记数量
     */
    private Integer noteCount;

    /**
     * 照片数量
     */
    private Integer photoCount;

    /**
     * 投喂次数
     */
    private Integer feedCount;

    /**
     * 心愿完成数
     */
    private Integer wishAchievedCount;
}