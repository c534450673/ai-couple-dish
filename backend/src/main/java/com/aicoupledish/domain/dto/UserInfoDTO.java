package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 用户信息DTO
 */
@Data
public class UserInfoDTO {

    private Long id;
    private String openid;
    private String nickName;
    private String avatarUrl;
    private String phone;
    private Integer gender;
    private Long coupleId;
    private String loveStartDate;
    private Integer memberLevel;
    private Integer status;

    /**
     * 情侣信息
     */
    private CoupleInfoDTO coupleInfo;
}