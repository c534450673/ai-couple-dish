package com.aicoupledish.service;

import com.aicoupledish.domain.dto.CoupleCodeDTO;
import com.aicoupledish.domain.dto.CoupleCodeDTO;
import com.aicoupledish.domain.dto.CoupleHomeDTO;
import com.aicoupledish.domain.dto.CoupleInfoDTO;
import com.aicoupledish.domain.req.BindCoupleReq;
import com.aicoupledish.domain.req.GenerateCodeReq;
import com.aicoupledish.domain.req.UnbindReq;

/**
 * 情侣服务接口
 */
public interface CoupleService {

    /**
     * 生成情侣码
     */
    String generateCoupleCode(Long userId, GenerateCodeReq req);

    /**
     * 绑定情侣
     */
    CoupleInfoDTO bindCouple(Long userId, BindCoupleReq req);

    /**
     * 获取情侣信息
     */
    CoupleInfoDTO getCoupleInfo(Long userId);

    /**
     * 获取情侣主页
     */
    CoupleHomeDTO getCoupleHome(Long userId);

    /**
     * 申请解绑
     */
    void applyUnbind(Long userId, UnbindReq req);

    /**
     * 确认解绑
     */
    void confirmUnbind(Long userId, Long coupleId);

    /**
     * 拒绝解绑
     */
    void rejectUnbind(Long userId, Long coupleId);

    /**
     * 验证情侣码
     */
    boolean validateCoupleCode(String coupleCode);

    /**
     * 获取恋爱计时信息
     */
    CoupleHomeDTO getLoveTimer(Long userId);

    /**
     * 检查是否有可恢复的情侣数据
     */
    CoupleInfoDTO checkRecoverableData(Long userId);

    /**
     * 恢复情侣数据
     */
    CoupleInfoDTO recoverCoupleData(Long userId, Long recordId);

    /**
     * 获取当前情侣码信息（含倒计时）
     */
    CoupleCodeDTO getCoupleCodeInfo(Long userId);

    /**
     * 刷新情侣码
     */
    String refreshCoupleCode(Long userId);

    /**
     * 发送情侣码过期提醒
     */
    void sendExpirationReminder();
}