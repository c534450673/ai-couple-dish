package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 私密菜单表
 */
@Data
@TableName("t_couple_menu")
public class CoupleMenu implements Serializable {

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
     * 创建者ID
     */
    private Long creatorId;

    /**
     * 餐厅名称
     */
    private String restaurantName;

    /**
     * 菜品名称
     */
    private String dishName;

    /**
     * 菜品分类/标签
     */
    private String dishCategory;

    /**
     * 人均价格
     */
    private BigDecimal price;

    /**
     * 位置信息
     */
    private String location;

    /**
     * 纬度
     */
    private BigDecimal latitude;

    /**
     * 经度
     */
    private BigDecimal longitude;

    /**
     * 私密笔记
     */
    private String note;

    /**
     * 评分1-5星
     */
    private Integer rating;

    /**
     * 用餐人IDs（JSON数组）
     */
    @TableField("eater_ids")
    private String eaterIds;

    /**
     * 用餐日期
     */
    private LocalDate eatenDate;

    /**
     * 状态：0-想去 1-去过 2-种草
     */
    private Integer status;

    /**
     * 点赞数
     */
    private Integer likeCount;

    /**
     * 是否收藏
     */
    private Integer isFavorite;

    /**
     * 照片URLs（JSON数组或逗号分隔）
     */
    private String photoUrls;

    /**
     * 照片数量
     */
    private Integer photoCount;

    /**
     * 关联纪念日ID
     */
    private Long anniversaryId;

    /**
     * 是否删除
     */
    @TableLogic
    private Integer isDeleted;

    /**
     * 删除时间
     */
    private LocalDateTime deleteTime;

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