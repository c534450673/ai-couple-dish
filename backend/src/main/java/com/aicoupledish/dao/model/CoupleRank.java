package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 情侣段位表
 */
@Data
@TableName("t_couple_rank")
public class CoupleRank implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 情侣ID
     */
    private Long coupleId;

    /**
     * 当前段位: bronze/silver/gold/platinum/diamond/king
     */
    private String currentRank;

    /**
     * 段位分数
     */
    private Integer rankScore;

    /**
     * 连续互动天数
     */
    private Integer consecutiveInteractionDays;

    /**
     * 恋爱温度
     */
    private Integer temperatureScore;

    /**
     * 最近晋升时间
     */
    private LocalDateTime promotionDate;

    /**
     * 降级预警
     */
    private Integer demotionWarning;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
