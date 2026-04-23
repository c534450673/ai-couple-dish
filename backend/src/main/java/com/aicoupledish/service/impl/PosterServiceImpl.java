package com.aicoupledish.service.impl;

import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.RandomUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.PosterDTO;
import com.aicoupledish.service.PosterService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 海报服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PosterServiceImpl implements PosterService {

    private final PosterTemplateMapper posterTemplateMapper;
    private final UserPosterMapper userPosterMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;
    private final AnniversaryMapper anniversaryMapper;
    private final CoupleMenuMapper coupleMenuMapper;
    private final FoodNoteMapper foodNoteMapper;

    @Override
    public List<PosterDTO.TemplateDTO> getTemplates(String posterType) {
        List<PosterTemplate> templates = posterTemplateMapper.selectList(
            new LambdaQueryWrapper<PosterTemplate>()
                .eq(PosterTemplate::getIsActive, 1)
                .eq(posterType != null, PosterTemplate::getTemplateType, posterType)
                .orderByAsc(PosterTemplate::getId)
        );

        return templates.stream().map(this::buildTemplateDTO).collect(Collectors.toList());
    }

    @Override
    @Transactional
    public PosterDTO generatePoster(Long userId, PosterDTO.GenerateReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 获取模板
        PosterTemplate template = null;
        if (req.getTemplateId() != null) {
            template = posterTemplateMapper.selectById(req.getTemplateId());
        } else if (req.getPosterType() != null) {
            // 如果没有指定模板ID，则根据海报类型查找默认模板
            template = posterTemplateMapper.selectOne(
                new LambdaQueryWrapper<PosterTemplate>()
                    .eq(PosterTemplate::getTemplateType, req.getPosterType())
                    .eq(PosterTemplate::getIsActive, 1)
                    .orderByAsc(PosterTemplate::getId)
                    .last("LIMIT 1")
            );
        }
        if (template == null || template.getIsActive() != 1) {
            throw new IllegalArgumentException("模板不存在或已禁用");
        }

        // 生成海报URL
        String posterUrl = generatePosterImage(template, req);

        // 保存海报记录
        UserPoster poster = new UserPoster();
        poster.setUserId(userId);
        poster.setCoupleId(user.getCoupleId());
        poster.setPosterType(req.getPosterType());
        poster.setTemplateId(req.getTemplateId());
        poster.setPosterUrl(posterUrl);
        poster.setInviteCode(generateInviteCode());
        userPosterMapper.insert(poster);

        log.info("生成海报: userId={}, posterId={}, type={}", userId, poster.getId(), req.getPosterType());

        return buildDTO(poster);
    }

    @Override
    public List<PosterDTO> getMyPosters(Long userId, String posterType, Integer limit) {
        List<UserPoster> posters = userPosterMapper.selectList(
            new LambdaQueryWrapper<UserPoster>()
                .eq(UserPoster::getUserId, userId)
                .eq(posterType != null, UserPoster::getPosterType, posterType)
                .orderByDesc(UserPoster::getCreateTime)
                .last("LIMIT " + (limit != null ? limit : 20))
        );

        return posters.stream().map(this::buildDTO).collect(Collectors.toList());
    }

    @Override
    public PosterDTO getPosterDetail(Long userId, Long posterId) {
        UserPoster poster = userPosterMapper.selectById(posterId);
        if (poster == null) {
            throw new IllegalArgumentException("海报不存在");
        }

        if (!poster.getUserId().equals(userId)) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildDTO(poster);
    }

    @Override
    @Transactional
    public void deletePoster(Long userId, Long posterId) {
        UserPoster poster = userPosterMapper.selectById(posterId);
        if (poster == null) {
            throw new IllegalArgumentException("海报不存在");
        }

        if (!poster.getUserId().equals(userId)) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        userPosterMapper.deleteById(posterId);
        log.info("删除海报: userId={}, posterId={}", userId, posterId);
    }

    @Override
    public PosterDTO getPosterShareData(Long userId, Long posterId) {
        UserPoster poster = userPosterMapper.selectById(posterId);
        if (poster == null) {
            throw new IllegalArgumentException("海报不存在");
        }

        if (!poster.getUserId().equals(userId)) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildDTO(poster);
    }

    /**
     * 生成海报图片URL
     */
    private String generatePosterImage(PosterTemplate template, PosterDTO.GenerateReq req) {
        String posterId = IdUtil.simpleUUID();
        return "/posters/" + posterId + ".png";
    }

    /**
     * 生成邀请码
     */
    private String generateInviteCode() {
        return RandomUtil.randomString(8).toUpperCase();
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private PosterDTO buildDTO(UserPoster poster) {
        PosterDTO dto = new PosterDTO();
        dto.setId(poster.getId());
        dto.setPosterType(poster.getPosterType());
        dto.setPosterTypeName(getPosterTypeName(poster.getPosterType()));
        dto.setTemplateId(poster.getTemplateId());
        dto.setPosterUrl(poster.getPosterUrl());
        dto.setInviteCode(poster.getInviteCode());
        dto.setCreateTime(poster.getCreateTime());

        PosterTemplate template = posterTemplateMapper.selectById(poster.getTemplateId());
        if (template != null) {
            dto.setTemplateName(template.getTemplateName());
        }

        return dto;
    }

    private PosterDTO.TemplateDTO buildTemplateDTO(PosterTemplate template) {
        PosterDTO.TemplateDTO dto = new PosterDTO.TemplateDTO();
        dto.setId(template.getId());
        dto.setTemplateCode(template.getTemplateCode());
        dto.setTemplateName(template.getTemplateName());
        dto.setTemplateType(template.getTemplateType());
        dto.setTemplateTypeName(getTemplateTypeName(template.getTemplateType()));
        dto.setTemplateConfig(template.getTemplateConfig());
        dto.setPreviewUrl(template.getPreviewUrl());
        dto.setIsActive(template.getIsActive() == 1);
        return dto;
    }

    private String getPosterTypeName(String type) {
        switch (type) {
            case "anniversary": return "纪念日海报";
            case "feed": return "恋爱动态海报";
            case "map": return "足迹地图海报";
            case "annual": return "年度总结海报";
            default: return type;
        }
    }

    private String getTemplateTypeName(String type) {
        return getPosterTypeName(type);
    }
}
