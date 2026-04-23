package com.aicoupledish.service.impl;

import cn.hutool.core.util.RandomUtil;
import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.SweetBombDTO;
import com.aicoupledish.service.NotificationService;
import com.aicoupledish.service.SweetBombService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

/**
 * 随机甜蜜炸弹服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SweetBombServiceImpl implements SweetBombService {

    private final SweetBombMapper sweetBombMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;
    private final AnniversaryMapper anniversaryMapper;
    private final CoupleMenuMapper coupleMenuMapper;
    private final TimeCapsuleMapper timeCapsuleMapper;
    private final NotificationService notificationService;

    @Override
    @Transactional
    public SweetBombDTO generateBomb(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 随机选择炸弹类型
        String[] bombTypes = {"memory", "data", "question", "festival"};
        String bombType = bombTypes[RandomUtil.randomInt(0, bombTypes.length)];

        SweetBombDTO.BombContent content = generateBombContent(user, bombType);

        SweetBomb bomb = new SweetBomb();
        bomb.setCoupleId(user.getCoupleId());
        bomb.setBombType(bombType);
        bomb.setContent(JSONUtil.toJsonStr(content));
        bomb.setSentTime(LocalDateTime.now());
        bomb.setIsRead(0);
        bomb.setIsAnswered(0);
        sweetBombMapper.insert(bomb);

        log.info("生成甜蜜炸弹: userId={}, bombId={}, type={}", userId, bomb.getId(), bombType);

        // 发送通知给伴侣
        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (couple != null) {
            Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
            notificationService.sendNotification(partnerId, 2,
                "💣 甜蜜炸弹", "你收到了一个甜蜜炸弹，快来看看吧~",
                bomb.getId(), "sweet_bomb");
        }

        return buildDTO(bomb);
    }

    @Override
    public List<SweetBombDTO> getUnreadBombs(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<SweetBomb> bombs = sweetBombMapper.selectList(
            new LambdaQueryWrapper<SweetBomb>()
                .eq(SweetBomb::getCoupleId, user.getCoupleId())
                .eq(SweetBomb::getIsRead, 0)
                .orderByDesc(SweetBomb::getSentTime)
        );

        return bombs.stream().map(this::buildDTO).collect(java.util.stream.Collectors.toList());
    }

    @Override
    public SweetBombDTO getBombDetail(Long userId, Long bombId) {
        SweetBomb bomb = sweetBombMapper.selectById(bombId);
        if (bomb == null) {
            throw new IllegalArgumentException("炸弹不存在");
        }

        User user = getUserById(userId);
        if (!bomb.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildDTO(bomb);
    }

    @Override
    @Transactional
    public void markAsRead(Long userId, Long bombId) {
        SweetBomb bomb = sweetBombMapper.selectById(bombId);
        if (bomb == null) {
            throw new IllegalArgumentException("炸弹不存在");
        }

        User user = getUserById(userId);
        if (!bomb.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        if (bomb.getIsRead() == 0) {
            bomb.setIsRead(1);
            sweetBombMapper.updateById(bomb);
        }
    }

    @Override
    @Transactional
    public void answerBomb(Long userId, Long bombId, String answerContent) {
        SweetBomb bomb = sweetBombMapper.selectById(bombId);
        if (bomb == null) {
            throw new IllegalArgumentException("炸弹不存在");
        }

        User user = getUserById(userId);
        if (!bomb.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        if (!"question".equals(bomb.getBombType())) {
            throw new IllegalArgumentException("此炸弹不需要回答");
        }

        bomb.setIsAnswered(1);
        bomb.setAnswerContent(answerContent);
        bomb.setAnswerTime(LocalDateTime.now());
        sweetBombMapper.updateById(bomb);

        log.info("回答甜蜜炸弹: userId={}, bombId={}", userId, bombId);
    }

    @Override
    public List<SweetBombDTO> getBombHistory(Long userId, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<SweetBomb> bombs = sweetBombMapper.selectList(
            new LambdaQueryWrapper<SweetBomb>()
                    .eq(SweetBomb::getCoupleId, user.getCoupleId())
                    .orderByDesc(SweetBomb::getSentTime)
                    .last("LIMIT " + (limit != null ? limit : 20))
        );

        return bombs.stream().map(this::buildDTO).collect(java.util.stream.Collectors.toList());
    }

    @Override
    public Integer getUnreadCount(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            return 0;
        }

        Long count = sweetBombMapper.selectCount(
            new LambdaQueryWrapper<SweetBomb>()
                    .eq(SweetBomb::getCoupleId, user.getCoupleId())
                    .eq(SweetBomb::getIsRead, 0)
        );

        return count != null ? count.intValue() : 0;
    }

    /**
     * 生成炸弹内容
     */
    private SweetBombDTO.BombContent generateBombContent(User user, String bombType) {
        SweetBombDTO.BombContent content = new SweetBombDTO.BombContent();

        switch (bombType) {
            case "memory":
                return generateMemoryBomb(user);
            case "data":
                return generateDataBomb(user);
            case "question":
                return generateQuestionBomb();
            case "festival":
                return generateFestivalBomb();
            default:
                content.setTitle("甜蜜惊喜");
                content.setDescription("一个神秘的小惊喜~");
                return content;
        }
    }

    private SweetBombDTO.BombContent generateMemoryBomb(User user) {
        SweetBombDTO.BombContent content = new SweetBombDTO.BombContent();
        content.setTitle("回忆时光机 💫");
        content.setDescription("还记得这些美好时刻吗？");

        // 获取纪念日回忆
        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                    .eq(Anniversary::getCoupleId, user.getCoupleId())
                    .last("LIMIT 3")
        );

        SweetBombDTO.MemoryData memoryData = new SweetBombDTO.MemoryData();
        memoryData.setMemoryType("anniversary");
        if (!anniversaries.isEmpty()) {
            Anniversary ann = anniversaries.get(RandomUtil.randomInt(0, anniversaries.size()));
            memoryData.setMemoryContent(ann.getName() + " - " + ann.getAnniversaryDate());
        }
        content.setMemoryData(memoryData);

        return content;
    }

    private SweetBombDTO.BombContent generateDataBomb(User user) {
        SweetBombDTO.BombContent content = new SweetBombDTO.BombContent();
        content.setTitle("恋爱数据站 📊");
        content.setDescription("来看看你们的恋爱数据吧~");

        Map<String, Object> statsData = new HashMap<>();

        // 统计约会次数
        Long menuCount = coupleMenuMapper.selectCount(
            new LambdaQueryWrapper<CoupleMenu>()
                    .eq(CoupleMenu::getCoupleId, user.getCoupleId())
        );
        statsData.put("totalDates", menuCount);

        // 统计纪念日
        Long anniversaryCount = anniversaryMapper.selectCount(
            new LambdaQueryWrapper<Anniversary>()
                    .eq(Anniversary::getCoupleId, user.getCoupleId())
        );
        statsData.put("totalAnniversaries", anniversaryCount);

        // 统计时光胶囊
        Long capsuleCount = timeCapsuleMapper.selectCount(
            new LambdaQueryWrapper<TimeCapsule>()
                    .eq(TimeCapsule::getCoupleId, user.getCoupleId())
        );
        statsData.put("totalCapsules", capsuleCount);

        content.setStatsData(statsData);

        return content;
    }

    private SweetBombDTO.BombContent generateQuestionBomb() {
        SweetBombDTO.BombContent content = new SweetBombDTO.BombContent();
        content.setTitle("心动问答 💕");
        content.setDescription("回答这个问题，让TA更了解你~");

        List<String> questions = Arrays.asList(
                "如果可以重新选择，你还会选择和TA在一起吗？",
                "TA做的最让你感动的事情是什么？",
                "你最想和TA一起去哪里旅行？",
                "你觉得TA最可爱的地方是什么？",
                "你最想对TA说的一句话是什么？",
                "你们的第一次约会是什么样的？",
                "TA的哪个习惯让你觉得最温暖？",
                "如果给你一天时间，你最想和TA做什么？"
        );

        content.setQuestion(questions.get(RandomUtil.randomInt(0, questions.size())));

        return content;
    }

    private SweetBombDTO.BombContent generateFestivalBomb() {
        SweetBombDTO.BombContent content = new SweetBombDTO.BombContent();
        content.setTitle("节日小提醒 🎉");
        content.setDescription("快来看看今天是什么特别的日子~");

        Map<String, Object> extraInfo = new HashMap<>();
        extraInfo.put("festivalType", "daily_reminder");
        content.setExtraInfo(extraInfo);

        return content;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private SweetBombDTO buildDTO(SweetBomb bomb) {
        SweetBombDTO dto = new SweetBombDTO();
        dto.setId(bomb.getId());
        dto.setBombType(bomb.getBombType());
        dto.setBombTypeName(getBombTypeName(bomb.getBombType()));
        dto.setSentTime(bomb.getSentTime());
        dto.setIsRead(bomb.getIsRead() == 1);
        dto.setIsAnswered(bomb.getIsAnswered() == 1);
        dto.setAnswerContent(bomb.getAnswerContent());
        dto.setAnswerTime(bomb.getAnswerTime());
        dto.setCreateTime(bomb.getCreateTime());

        // 解析内容
        if (bomb.getContent() != null) {
            SweetBombDTO.BombContent content = JSONUtil.toBean(bomb.getContent(), SweetBombDTO.BombContent.class);
            dto.setContent(content);
        }

        return dto;
    }

    private String getBombTypeName(String type) {
        switch (type) {
            case "memory": return "回忆时光机";
            case "data": return "恋爱数据站";
            case "question": return "心动问答";
            case "festival": return "节日提醒";
            default: return type;
        }
    }
}
