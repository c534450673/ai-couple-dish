package com.aicoupledish.domain.req;

import lombok.Data;

/**
 * 解绑情侣请求
 */
@Data
public class UnbindReq {

    /**
     * 解绑选项：keep-保留数据 delete-删除数据
     */
    private String option;
}