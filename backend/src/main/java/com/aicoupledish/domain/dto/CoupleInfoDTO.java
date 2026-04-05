package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 情侣信息DTO
 */
@Data
public class CoupleInfoDTO {

    private Long id;
    private String coupleCode;
    private Long user1Id;
    private Long user2Id;
    private String startDate;
    private Integer loveDays;
    private String coupleNickname;
    private Integer status;

    /**
     * 伴侣信息
     */
    private PartnerInfoDTO partner;

    /**
     * 可恢复天数（用于解绑记录）
     */
    private Integer recoverableDays;

    /**
     * 解绑记录ID（用于恢复数据）
     */
    private Long unbindRecordId;
}