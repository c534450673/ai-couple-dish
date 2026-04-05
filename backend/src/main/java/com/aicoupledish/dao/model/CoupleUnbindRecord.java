package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 情侣解绑记录表
 */
@Data
@TableName("t_couple_unbind_record")
public class CoupleUnbindRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 原情侣关系ID
     */
    private Long coupleId;

    /**
     * 用户1ID
     */
    private Long user1Id;

    /**
     * 用户2ID
     */
    private Long user2Id;

    /**
     * 申请解绑者ID
     */
    private Long applicantId;

    /**
     * 恋爱开始日期
     */
    private LocalDateTime loveStartDate;

    /**
     * 恋爱天数
     */
    private Integer loveDays;

    /**
     * 情侣昵称
     */
    private String coupleNickname;

    /**
     * 备份数据（JSON格式）
     */
    private String backupData;

    /**
     * 解绑时间
     */
    private LocalDateTime unbindTime;

    /**
     * 数据过期时间（30天后）
     */
    private LocalDateTime dataExpireTime;

    /**
     * 状态：0-已解绑可恢复 1-已恢复 2-已过期清除
     */
    private Integer status;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;
}
