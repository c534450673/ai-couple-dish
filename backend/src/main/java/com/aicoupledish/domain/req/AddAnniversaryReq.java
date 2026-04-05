package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

/**
 * 添加纪念日请求
 */
@Data
public class AddAnniversaryReq {

    /**
     * 纪念日名称
     */
    @NotBlank(message = "纪念日名称不能为空")
    private String name;

    /**
     * 纪念日日期（阳历日期，兼容旧数据）
     */
    @NotNull(message = "纪念日日期不能为空")
    private String anniversaryDate;

    /**
     * 是否农历日期：0-阳历 1-农历
     */
    private Integer isLunarDate;

    /**
     * 农历月（1-12）
     */
    private Integer lunarMonth;

    /**
     * 农历日（1-30）
     */
    private Integer lunarDay;

    /**
     * 类型：1-相识 2-恋爱 3-表白 4-其他
     */
    @NotNull(message = "纪念日类型不能为空")
    private Integer anniversaryType;

    /**
     * 提前提醒天数
     */
    private Integer remindDaysBefore;

    /**
     * 是否自动提醒
     */
    private Integer autoRemind;
}