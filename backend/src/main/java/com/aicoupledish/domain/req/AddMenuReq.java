package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import java.math.BigDecimal;
import java.util.List;

/**
 * 添加菜单请求
 */
@Data
public class AddMenuReq {

    /**
     * 餐厅名称
     */
    @NotBlank(message = "餐厅名称不能为空")
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
     * 用餐人IDs
     */
    private List<Long> eaterIds;

    /**
     * 用餐日期
     */
    private String eatenDate;

    /**
     * 状态：0-想去 1-去过 2-种草
     */
    private Integer status;

    /**
     * 关联纪念日ID
     */
    private Long anniversaryId;

    /**
     * 照片URLs（逗号分隔）
     */
    private String photoUrls;
}