package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 伴侣信息DTO
 */
@Data
public class PartnerInfoDTO {

    private Long id;
    private String nickName;
    private String avatarUrl;
    private Integer gender;
}