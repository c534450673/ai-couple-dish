package com.aicoupledish.service;

import com.aicoupledish.domain.dto.CoupleTreeDTO;
import com.aicoupledish.domain.req.WaterTreeReq;

import java.util.List;

/**
 * 情侣爱心树服务接口
 */
public interface CoupleTreeService {

    /**
     * 获取爱心树信息
     */
    CoupleTreeDTO getTreeInfo(Long userId);

    /**
     * 浇水（增加养分）
     */
    void waterTree(Long userId, WaterTreeReq req);

    /**
     * 增加养分（内部调用）
     */
    void addNutrient(Long coupleId, Long userId, Integer amount, String sourceAction, String remark);

    /**
     * 获取养分日志
     */
    List<CoupleTreeDTO.NutrientLogInfo> getNutrientLogs(Long userId, Integer limit);

    /**
     * 切换皮肤
     */
    void changeSkin(Long userId, String skinId);

    /**
     * 获取可用皮肤列表
     */
    List<CoupleTreeDTO.SkinInfo> getAvailableSkins(Long userId);
}
