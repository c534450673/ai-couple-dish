package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.CoupleTreeMapper;
import com.aicoupledish.dao.mapper.TreeNutrientLogMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.CoupleTree;
import com.aicoupledish.dao.model.TreeNutrientLog;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.CoupleTreeDTO;
import com.aicoupledish.domain.req.WaterTreeReq;
import com.aicoupledish.service.CoupleTreeService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 情侣爱心树服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CoupleTreeServiceImpl implements CoupleTreeService {

    private final CoupleTreeMapper coupleTreeMapper;
    private final TreeNutrientLogMapper treeNutrientLogMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    /**
     * 等级配置：每级所需累计养分
     */
    private static final long[] LEVEL_NUTRIENTS = {
        0,      // 1级
        100,    // 2级
        300,    // 3级
        600,    // 4级
        1000,   // 5级
        1500,   // 6级
        2100,   // 7级
        2800,   // 8级
        3600,   // 9级
        4500,   // 10级
        5500,   // 11级
        6600,   // 12级
        7800,   // 13级
        9100,   // 14级
        10500,  // 15级
    };

    /**
     * 等级名称
     */
    private static final String[] LEVEL_NAMES = {
        "幼苗", "小树", "成长树", "茁壮树", "茂盛树",
        "开花树", "结果树", "智慧树", "幸福树", "永恒树",
        "传奇树", "神话树", "圣树", "神树", "世界树"
    };

    @Override
    public CoupleTreeDTO getTreeInfo(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleTree tree = getOrCreateTree(user.getCoupleId());
        return buildDTO(tree, userId);
    }

    @Override
    @Transactional
    public void waterTree(Long userId, WaterTreeReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        int amount = req.getNutrientAmount() != null ? req.getNutrientAmount() : 10;
        addNutrient(user.getCoupleId(), userId, amount,
            req.getSourceAction() != null ? req.getSourceAction() : "manual_water",
            req.getRemark());
    }

    @Override
    @Transactional
    public void addNutrient(Long coupleId, Long userId, Integer amount, String sourceAction, String remark) {
        CoupleTree tree = getOrCreateTree(coupleId);

        // 使用原子更新避免竞态条件
        coupleTreeMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<CoupleTree>()
                .eq(CoupleTree::getId, tree.getId())
                .setSql("total_nutrient = total_nutrient + " + amount)
                .setSql("current_level_nutrient = current_level_nutrient + " + amount));

        // 重新查询更新后的数据
        tree = coupleTreeMapper.selectById(tree.getId());

        // 检查是否升级
        int newLevel = calculateLevel(tree.getTotalNutrient());
        if (newLevel > tree.getLevel()) {
            tree.setLevel(newLevel);
            log.info("爱心树升级: coupleId={}, newLevel={}", coupleId, newLevel);
            // TODO: 发送升级通知
        }

        // 更新当前等级养分
        long currentLevelBase = LEVEL_NUTRIENTS[Math.min(tree.getLevel() - 1, LEVEL_NUTRIENTS.length - 1)];
        long nextLevelBase = LEVEL_NUTRIENTS[Math.min(tree.getLevel(), LEVEL_NUTRIENTS.length - 1)];
        tree.setCurrentLevelNutrient(tree.getTotalNutrient() - currentLevelBase);

        coupleTreeMapper.updateById(tree);

        // 记录日志
        TreeNutrientLog nutrientLog = new TreeNutrientLog();
        nutrientLog.setCoupleId(coupleId);
        nutrientLog.setUserId(userId);
        nutrientLog.setNutrientAmount(amount);
        nutrientLog.setSourceAction(sourceAction);
        nutrientLog.setRemark(remark);
        treeNutrientLogMapper.insert(nutrientLog);

        log.info("爱心树增加养分: coupleId={}, userId={}, amount={}, source={}", coupleId, userId, amount, sourceAction);
    }

    @Override
    public List<CoupleTreeDTO.NutrientLogInfo> getNutrientLogs(Long userId, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<TreeNutrientLog> logs = treeNutrientLogMapper.selectList(
            new LambdaQueryWrapper<TreeNutrientLog>()
                .eq(TreeNutrientLog::getCoupleId, user.getCoupleId())
                .orderByDesc(TreeNutrientLog::getCreateTime)
                .last("LIMIT " + (limit != null ? limit : 20))
        );

        return logs.stream().map(this::buildNutrientLogInfo).collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void changeSkin(Long userId, String skinId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleTree tree = getOrCreateTree(user.getCoupleId());

        // 检查皮肤是否解锁
        List<CoupleTreeDTO.SkinInfo> skins = getAvailableSkins(userId);
        boolean unlocked = skins.stream().anyMatch(s -> s.getSkinId().equals(skinId) && s.getUnlocked());
        if (!unlocked) {
            throw new IllegalArgumentException("该皮肤尚未解锁");
        }

        tree.setSkinId(skinId);
        coupleTreeMapper.updateById(tree);

        log.info("更换爱心树皮肤: userId={}, skinId={}", userId, skinId);
    }

    @Override
    public List<CoupleTreeDTO.SkinInfo> getAvailableSkins(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleTree tree = getOrCreateTree(user.getCoupleId());
        int currentLevel = tree.getLevel();

        List<CoupleTreeDTO.SkinInfo> skins = new ArrayList<>();

        // 默认皮肤
        CoupleTreeDTO.SkinInfo defaultSkin = new CoupleTreeDTO.SkinInfo();
        defaultSkin.setSkinId("default");
        defaultSkin.setSkinName("默认");
        defaultSkin.setPreviewUrl("/skins/default.png");
        defaultSkin.setRequiredLevel(1);
        defaultSkin.setUnlocked(true);
        skins.add(defaultSkin);

        // 春天皮肤
        CoupleTreeDTO.SkinInfo springSkin = new CoupleTreeDTO.SkinInfo();
        springSkin.setSkinId("spring");
        springSkin.setSkinName("春日樱花");
        springSkin.setPreviewUrl("/skins/spring.png");
        springSkin.setRequiredLevel(3);
        springSkin.setUnlocked(currentLevel >= 3);
        skins.add(springSkin);

        // 夏天皮肤
        CoupleTreeDTO.SkinInfo summerSkin = new CoupleTreeDTO.SkinInfo();
        summerSkin.setSkinId("summer");
        summerSkin.setSkinName("夏日清凉");
        summerSkin.setPreviewUrl("/skins/summer.png");
        summerSkin.setRequiredLevel(5);
        summerSkin.setUnlocked(currentLevel >= 5);
        skins.add(summerSkin);

        // 秋天皮肤
        CoupleTreeDTO.SkinInfo autumnSkin = new CoupleTreeDTO.SkinInfo();
        autumnSkin.setSkinId("autumn");
        autumnSkin.setSkinName("秋日金桂");
        autumnSkin.setPreviewUrl("/skins/autumn.png");
        autumnSkin.setRequiredLevel(7);
        autumnSkin.setUnlocked(currentLevel >= 7);
        skins.add(autumnSkin);

        // 冬天皮肤
        CoupleTreeDTO.SkinInfo winterSkin = new CoupleTreeDTO.SkinInfo();
        winterSkin.setSkinId("winter");
        winterSkin.setSkinName("冬日雪松");
        winterSkin.setPreviewUrl("/skins/winter.png");
        winterSkin.setRequiredLevel(10);
        winterSkin.setUnlocked(currentLevel >= 10);
        skins.add(winterSkin);

        return skins;
    }

    /**
     * 获取或创建爱心树
     */
    private CoupleTree getOrCreateTree(Long coupleId) {
        CoupleTree tree = coupleTreeMapper.selectOne(
            new LambdaQueryWrapper<CoupleTree>()
                .eq(CoupleTree::getCoupleId, coupleId)
        );

        if (tree == null) {
            tree = new CoupleTree();
            tree.setCoupleId(coupleId);
            tree.setLevel(1);
            tree.setTotalNutrient(0L);
            tree.setCurrentLevelNutrient(0L);
            tree.setSkinId("default");
            coupleTreeMapper.insert(tree);
            log.info("创建爱心树: coupleId={}", coupleId);
        }

        return tree;
    }

    /**
     * 计算等级
     */
    private int calculateLevel(Long totalNutrient) {
        for (int i = LEVEL_NUTRIENTS.length - 1; i >= 0; i--) {
            if (totalNutrient >= LEVEL_NUTRIENTS[i]) {
                return i + 1;
            }
        }
        return 1;
    }

    /**
     * 获取今日获得养分
     */
    private Integer getTodayNutrient(Long coupleId) {
        LocalDateTime startOfDay = LocalDate.now().atStartOfDay();
        LocalDateTime endOfDay = startOfDay.plusDays(1);

        List<TreeNutrientLog> logs = treeNutrientLogMapper.selectList(
            new LambdaQueryWrapper<TreeNutrientLog>()
                .eq(TreeNutrientLog::getCoupleId, coupleId)
                .ge(TreeNutrientLog::getCreateTime, startOfDay)
                .lt(TreeNutrientLog::getCreateTime, endOfDay)
        );

        return logs.stream().mapToInt(TreeNutrientLog::getNutrientAmount).sum();
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private CoupleTreeDTO buildDTO(CoupleTree tree, Long userId) {
        CoupleTreeDTO dto = new CoupleTreeDTO();
        dto.setId(tree.getId());
        dto.setLevel(tree.getLevel());
        dto.setLevelName(getLevelName(tree.getLevel()));
        dto.setTotalNutrient(tree.getTotalNutrient());
        dto.setCurrentLevelNutrient(tree.getCurrentLevelNutrient());
        dto.setSkinId(tree.getSkinId());
        dto.setCreateTime(tree.getCreateTime());

        // 计算升级所需养分
        int levelIndex = Math.min(tree.getLevel() - 1, LEVEL_NUTRIENTS.length - 1);
        int nextLevelIndex = Math.min(tree.getLevel(), LEVEL_NUTRIENTS.length - 1);
        long currentLevelBase = LEVEL_NUTRIENTS[levelIndex];
        long nextLevelBase = LEVEL_NUTRIENTS[nextLevelIndex];

        dto.setNextLevelNutrient(nextLevelBase - currentLevelBase);

        // 计算进度百分比
        if (nextLevelBase > currentLevelBase) {
            long progress = tree.getTotalNutrient() - currentLevelBase;
            long needed = nextLevelBase - currentLevelBase;
            dto.setProgressPercent((int) (progress * 100 / needed));
        } else {
            dto.setProgressPercent(100);
        }

        // 获取今日养分
        dto.setTodayNutrient(getTodayNutrient(tree.getCoupleId()));

        // 获取可用皮肤
        dto.setAvailableSkins(getAvailableSkins(userId));

        return dto;
    }

    private CoupleTreeDTO.NutrientLogInfo buildNutrientLogInfo(TreeNutrientLog log) {
        CoupleTreeDTO.NutrientLogInfo info = new CoupleTreeDTO.NutrientLogInfo();
        info.setId(log.getId());
        info.setUserId(log.getUserId());
        info.setNutrientAmount(log.getNutrientAmount());
        info.setSourceAction(log.getSourceAction());
        info.setSourceActionName(getActionName(log.getSourceAction()));
        info.setRemark(log.getRemark());
        info.setCreateTime(log.getCreateTime());

        User user = userMapper.selectById(log.getUserId());
        if (user != null) {
            info.setUserName(user.getNickName());
            info.setUserAvatar(user.getAvatarUrl());
        }

        return info;
    }

    private String getLevelName(int level) {
        if (level >= 1 && level <= LEVEL_NAMES.length) {
            return LEVEL_NAMES[level - 1];
        }
        return "世界树";
    }

    private String getActionName(String action) {
        if (action == null) return "未知";
        switch (action) {
            case "manual_water": return "手动浇水";
            case "daily_task": return "每日任务";
            case "greeting": return "早安晚安打卡";
            case "anniversary": return "纪念日奖励";
            case "feed": return "投喂奖励";
            case "wish_achieved": return "心愿实现";
            default: return action;
        }
    }
}
