package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 关系气象站表
 */
@Data
@TableName("t_relationship_weather")
public class RelationshipWeather implements Serializable {

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
     * 等级: sunny/cloudy/rainy/stormy
     */
    private String weatherLevel;

    /**
     * 互动分数
     */
    private Integer interactionScore;

    /**
     * 距上次互动天数
     */
    private Integer daysSinceLastInteraction;

    /**
     * 恋爱温度
     */
    private Integer temperatureScore;

    /**
     * 是否已发送预警
     */
    private Integer alertSent;

    /**
     * 预警类型
     */
    private String alertType;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
