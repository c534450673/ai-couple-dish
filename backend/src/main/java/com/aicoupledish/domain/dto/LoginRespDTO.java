package com.aicoupledish.domain.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 登录响应DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginRespDTO {

    private String token;
    private UserInfoDTO userInfo;
}