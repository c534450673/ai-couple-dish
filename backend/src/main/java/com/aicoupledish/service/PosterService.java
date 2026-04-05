package com.aicoupledish.service;

import com.aicoupledish.domain.dto.PosterDTO;

import java.util.List;

/**
 * 海报服务接口
 */
public interface PosterService {

    /**
     * 获取海报模板列表
     */
    List<PosterDTO.TemplateDTO> getTemplates(String posterType);

    /**
     * 生成海报
     */
    PosterDTO generatePoster(Long userId, PosterDTO.GenerateReq req);

    /**
     * 获取用户海报列表
     */
    List<PosterDTO> getMyPosters(Long userId, String posterType, Integer limit);

    /**
     * 获取海报详情
     */
    PosterDTO getPosterDetail(Long userId, Long posterId);

    /**
     * 删除海报
     */
    void deletePoster(Long userId, Long posterId);

    /**
     * 获取海报分享数据
     */
    PosterDTO getPosterShareData(Long userId, Long posterId);
}
