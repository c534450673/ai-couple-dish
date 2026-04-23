package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.AnniversaryMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Anniversary;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.AnniversaryDTO;
import com.aicoupledish.domain.req.AddAnniversaryReq;
import com.aicoupledish.domain.req.ReminderConfigReq;
import com.aicoupledish.service.AnniversaryService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 纪念日服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AnniversaryServiceImpl implements AnniversaryService {

    private final AnniversaryMapper anniversaryMapper;
    private final UserMapper userMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    @Override
    public List<AnniversaryDTO> getAnniversaryList(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                .eq(Anniversary::getCoupleId, user.getCoupleId())
                .orderByAsc(Anniversary::getAnniversaryDate)
        );

        return anniversaries.stream().map(this::buildAnniversaryDTO).collect(Collectors.toList());
    }

    @Override
    public List<AnniversaryDTO> getUpcomingAnniversaries(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LocalDate today = LocalDate.now();
        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                .eq(Anniversary::getCoupleId, user.getCoupleId())
        );

        return anniversaries.stream()
                .sorted((a, b) -> {
                    LocalDate aNext = calculateNextAnniversaryDate(a.getAnniversaryDate());
                    LocalDate bNext = calculateNextAnniversaryDate(b.getAnniversaryDate());
                    return aNext.compareTo(bNext);
                })
                .map(this::buildAnniversaryDTO)
                .collect(Collectors.toList());
    }

    @Override
    public AnniversaryDTO getNextAnniversary(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            return null;
        }

        LocalDate today = LocalDate.now();
        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                .eq(Anniversary::getCoupleId, user.getCoupleId())
                .orderByAsc(Anniversary::getAnniversaryDate)
        );

        for (Anniversary a : anniversaries) {
            LocalDate nextDate = calculateNextAnniversaryDate(a.getAnniversaryDate());
            if (!nextDate.isBefore(today)) {
                AnniversaryDTO dto = new AnniversaryDTO();
                dto.setId(a.getId());
                dto.setName(a.getName());
                dto.setAnniversaryDate(a.getAnniversaryDate().toString());
                dto.setAnniversaryType(a.getAnniversaryType());
                dto.setTypeName(getTypeName(a.getAnniversaryType()));
                dto.setRemindDaysBefore(a.getRemindDaysBefore());
                dto.setAutoRemind(a.getAutoRemind());
                dto.setDaysUntil((int) ChronoUnit.DAYS.between(today, nextDate));
                dto.setIsPast(false);
                return dto;
            }
        }
        return null;
    }

    @Override
    @Transactional
    public Long addAnniversary(Long userId, AddAnniversaryReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 检查恋爱日是否已存在（只能有一个恋爱日）
        if (req.getAnniversaryType() == 2) {
            Anniversary existing = anniversaryMapper.selectOne(
                new LambdaQueryWrapper<Anniversary>()
                    .eq(Anniversary::getCoupleId, user.getCoupleId())
                    .eq(Anniversary::getAnniversaryType, 2)
            );
            if (existing != null) {
                throw BusinessException.ANNIVERSARY_ALREADY_EXISTS;
            }
        }

        Anniversary anniversary = new Anniversary();
        anniversary.setCoupleId(user.getCoupleId());
        anniversary.setCreatorId(userId);
        anniversary.setName(req.getName());
        anniversary.setAnniversaryDate(LocalDate.parse(req.getAnniversaryDate()));
        anniversary.setAnniversaryType(req.getAnniversaryType());
        anniversary.setRemindDaysBefore(req.getRemindDaysBefore() != null ? req.getRemindDaysBefore() : 7);
        anniversary.setAutoRemind(req.getAutoRemind() != null ? req.getAutoRemind() : 1);

        anniversaryMapper.insert(anniversary);

        log.info("添加纪念日: userId={}, anniversaryId={}", userId, anniversary.getId());
        return anniversary.getId();
    }

    @Override
    @Transactional
    public void updateAnniversary(Long userId, Long anniversaryId, AddAnniversaryReq req) {
        User user = getUserById(userId);
        Anniversary anniversary = anniversaryMapper.selectById(anniversaryId);

        if (anniversary == null) {
            throw BusinessException.ANNIVERSARY_NOT_FOUND;
        }

        if (!anniversary.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        // 恋爱日类型不能修改
        if (anniversary.getAnniversaryType() == 2 && req.getAnniversaryType() != null && req.getAnniversaryType() != 2) {
            throw BusinessException.ANNIVERSARY_CANNOT_DELETE;
        }

        if (req.getName() != null) {
            anniversary.setName(req.getName());
        }
        if (req.getAnniversaryDate() != null) {
            anniversary.setAnniversaryDate(LocalDate.parse(req.getAnniversaryDate()));
        }
        if (req.getAnniversaryType() != null) {
            anniversary.setAnniversaryType(req.getAnniversaryType());
        }
        if (req.getRemindDaysBefore() != null) {
            anniversary.setRemindDaysBefore(req.getRemindDaysBefore());
        }
        if (req.getAutoRemind() != null) {
            anniversary.setAutoRemind(req.getAutoRemind());
        }

        anniversaryMapper.updateById(anniversary);
        log.info("更新纪念日: userId={}, anniversaryId={}", userId, anniversaryId);
    }

    @Override
    @Transactional
    public void deleteAnniversary(Long userId, Long anniversaryId) {
        User user = getUserById(userId);
        Anniversary anniversary = anniversaryMapper.selectById(anniversaryId);

        if (anniversary == null) {
            throw BusinessException.ANNIVERSARY_NOT_FOUND;
        }

        if (!anniversary.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        // 恋爱日不能删除
        if (anniversary.getAnniversaryType() == 2) {
            throw BusinessException.ANNIVERSARY_CANNOT_DELETE;
        }

        anniversaryMapper.deleteById(anniversaryId);
        log.info("删除纪念日: userId={}, anniversaryId={}", userId, anniversaryId);
    }

    @Override
    public AnniversaryDTO checkTodayAnniversary(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            return null;
        }

        LocalDate today = LocalDate.now();
        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                .eq(Anniversary::getCoupleId, user.getCoupleId())
        );

        // 检查是否有今天的纪念日（同月同日）
        for (Anniversary a : anniversaries) {
            LocalDate anniversaryDate = a.getAnniversaryDate();
            if (anniversaryDate.getMonthValue() == today.getMonthValue() &&
                anniversaryDate.getDayOfMonth() == today.getDayOfMonth()) {
                AnniversaryDTO dto = new AnniversaryDTO();
                dto.setId(a.getId());
                dto.setName(a.getName());
                dto.setAnniversaryDate(a.getAnniversaryDate().toString());
                dto.setAnniversaryType(a.getAnniversaryType());
                dto.setTypeName(getTypeName(a.getAnniversaryType()));
                dto.setDaysUntil(0);
                dto.setIsPast(false);
                return dto;
            }
        }
        return null;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private LocalDate calculateNextAnniversaryDate(LocalDate anniversaryDate) {
        LocalDate today = LocalDate.now();
        LocalDate next = anniversaryDate;

        // 当天纪念日应该返回当天，只有过去的日期才需要加一年
        while (next.isBefore(today)) {
            next = next.plusYears(1);
        }
        return next;
    }

    private String getTypeName(Integer type) {
        switch (type) {
            case 1: return "相识";
            case 2: return "恋爱";
            case 3: return "表白";
            case 4: return "其他";
            default: return "其他";
        }
    }

    private AnniversaryDTO buildAnniversaryDTO(Anniversary a) {
        LocalDate today = LocalDate.now();
        LocalDate nextDate = calculateNextAnniversaryDate(a.getAnniversaryDate());

        AnniversaryDTO dto = new AnniversaryDTO();
        dto.setId(a.getId());
        dto.setName(a.getName());
        dto.setAnniversaryDate(a.getAnniversaryDate().toString());
        dto.setAnniversaryType(a.getAnniversaryType());
        dto.setTypeName(getTypeName(a.getAnniversaryType()));
        dto.setRemindDaysBefore(a.getRemindDaysBefore());
        dto.setAutoRemind(a.getAutoRemind());
        dto.setDaysUntil((int) ChronoUnit.DAYS.between(today, nextDate));
        dto.setIsPast(nextDate.isBefore(today));
        dto.setRemindChannels(a.getRemindChannels());
        dto.setRemindHour(a.getRemindHour());

        return dto;
    }

    @Override
    @Transactional
    public void updateReminderConfig(Long userId, ReminderConfigReq req) {
        User user = getUserById(userId);
        Anniversary anniversary = anniversaryMapper.selectById(req.getAnniversaryId());

        if (anniversary == null) {
            throw BusinessException.ANNIVERSARY_NOT_FOUND;
        }

        if (!anniversary.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        // 更新提醒配置
        if (req.getAutoRemind() != null) {
            anniversary.setAutoRemind(req.getAutoRemind());
        }
        if (req.getRemindDaysBefore() != null) {
            anniversary.setRemindDaysBefore(req.getRemindDaysBefore());
        }
        if (req.getRemindChannels() != null) {
            anniversary.setRemindChannels(req.getRemindChannels());
        }
        if (req.getRemindHour() != null) {
            anniversary.setRemindHour(req.getRemindHour());
        }
        if (req.getWechatRemindEnabled() != null) {
            anniversary.setWechatRemindEnabled(req.getWechatRemindEnabled());
        }
        if (req.getSmsRemindEnabled() != null) {
            anniversary.setSmsRemindEnabled(req.getSmsRemindEnabled());
        }
        if (req.getAppRemindEnabled() != null) {
            anniversary.setAppRemindEnabled(req.getAppRemindEnabled());
        }

        anniversaryMapper.updateById(anniversary);
        log.info("更新纪念日提醒配置: userId={}, anniversaryId={}", userId, req.getAnniversaryId());
    }
}