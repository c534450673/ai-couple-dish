package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.DeepQaDTO;
import com.aicoupledish.service.impl.DeepQaServiceImpl;
import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.apache.ibatis.builder.MapperBuilderAssistant;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 深度问答服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("深度问答服务测试")
class DeepQaServiceTest {

    @Mock
    private DeepQuestionMapper deepQuestionMapper;

    @Mock
    private CoupleQaProgressMapper coupleQaProgressMapper;

    @Mock
    private DeepQaAnswerMapper deepQaAnswerMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @InjectMocks
    private DeepQaServiceImpl deepQaService;

    private Long userId;
    private Long partnerId;
    private Long coupleId;
    private User user;
    private User partner;
    private Couple couple;
    private DeepQuestion question;
    private CoupleQaProgress progress;

    @BeforeAll
    static void initMybatisPlusCache() {
        // Initialize MyBatis-Plus lambda cache for entity classes used in LambdaQueryWrapper/LambdaUpdateWrapper
        // Required for pure Mockito tests (without Spring context) that use lambda wrappers
        MybatisConfiguration configuration = new MybatisConfiguration();
        MapperBuilderAssistant assistant = new MapperBuilderAssistant(configuration, "");
        if (TableInfoHelper.getTableInfo(CoupleQaProgress.class) == null) {
            TableInfoHelper.initTableInfo(assistant, CoupleQaProgress.class);
        }
        if (TableInfoHelper.getTableInfo(DeepQaAnswer.class) == null) {
            TableInfoHelper.initTableInfo(assistant, DeepQaAnswer.class);
        }
        if (TableInfoHelper.getTableInfo(DeepQuestion.class) == null) {
            TableInfoHelper.initTableInfo(assistant, DeepQuestion.class);
        }
    }

    @BeforeEach
    void setUp() {
        userId = 1L;
        partnerId = 2L;
        coupleId = 100L;

        user = new User();
        user.setId(userId);
        user.setNickName("小明");
        user.setAvatarUrl("/avatar/1.png");
        user.setCoupleId(coupleId);

        partner = new User();
        partner.setId(partnerId);
        partner.setNickName("小红");
        partner.setAvatarUrl("/avatar/2.png");

        couple = new Couple();
        couple.setId(coupleId);
        couple.setUser1Id(userId);
        couple.setUser2Id(partnerId);
        couple.setStatus(1);

        question = new DeepQuestion();
        question.setId(10L);
        question.setWeekNumber(1);
        question.setQuestionText("你认为两个人在一起最重要的是什么？");
        question.setQuestionType("open");
        question.setCategory("relationship");
        question.setSortOrder(1);
        question.setIsActive(1);

        progress = new CoupleQaProgress();
        progress.setId(1L);
        progress.setCoupleId(coupleId);
        progress.setCurrentWeek(1);
        progress.setCurrentQuestion(1);
        progress.setTotalCompleted(0);
    }

    @Nested
    @DisplayName("获取当前问题")
    class GetCurrentQuestion {

        @Test
        @DisplayName("获取当前问题-成功")
        void getCurrentQuestion_success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            DeepQaDTO result = deepQaService.getCurrentQuestion(userId);

            // Then
            assertNotNull(result);
            assertEquals(question.getId(), result.getId());
            assertEquals(question.getQuestionText(), result.getQuestionText());
            assertEquals("感情", result.getCategoryName());
        }

        @Test
        @DisplayName("获取当前问题-用户未绑定情侣应抛异常")
        void getCurrentQuestion_notBound_throw() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.getCurrentQuestion(userId));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }

        @Test
        @DisplayName("获取当前问题-用户不存在应抛异常")
        void getCurrentQuestion_userNotFound_throw() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.getCurrentQuestion(userId));
            assertEquals(BusinessException.USER_NOT_FOUND.getCode(), ex.getCode());
        }

        @Test
        @DisplayName("获取当前问题-没有可回答的问题返回null")
        void getCurrentQuestion_noQuestion_returnNull() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            DeepQaDTO result = deepQaService.getCurrentQuestion(userId);

            // Then
            assertNull(result);
        }

        @Test
        @DisplayName("获取当前问题-已回答问题包含我的答案")
        void getCurrentQuestion_withMyAnswer() {
            // Given
            DeepQaAnswer myAnswer = new DeepQaAnswer();
            myAnswer.setId(1L);
            myAnswer.setQuestionId(question.getId());
            myAnswer.setUserId(userId);
            myAnswer.setAnswerText("信任");
            myAnswer.setIsRevealed(0);
            myAnswer.setCreateTime(LocalDateTime.now());

            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(myAnswer);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            DeepQaDTO result = deepQaService.getCurrentQuestion(userId);

            // Then
            assertNotNull(result);
            assertNotNull(result.getMyAnswer());
            assertEquals("信任", result.getMyAnswer().getAnswerText());
            assertFalse(result.getIsRevealed());
        }
    }

    @Nested
    @DisplayName("获取周问题列表")
    class GetWeekQuestions {

        @Test
        @DisplayName("获取周问题列表-成功")
        void getWeekQuestions_success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(deepQuestionMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(question));
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            List<DeepQaDTO> result = deepQaService.getWeekQuestions(userId, 1);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals(question.getQuestionText(), result.get(0).getQuestionText());
        }

        @Test
        @DisplayName("获取周问题列表-未绑定情侣应抛异常")
        void getWeekQuestions_notBound_throw() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.getWeekQuestions(userId, 1));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("提交答案")
    class SubmitAnswer {

        @Test
        @DisplayName("提交答案-成功")
        void submitAnswer_success() {
            // Given
            DeepQaDTO.SubmitAnswerReq req = new DeepQaDTO.SubmitAnswerReq();
            req.setQuestionId(10L);
            req.setAnswerText("信任和包容");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(deepQaAnswerMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(7L);
            when(coupleQaProgressMapper.update(any(), any(LambdaUpdateWrapper.class))).thenReturn(1);
            when(deepQaAnswerMapper.insert(any(DeepQaAnswer.class))).thenReturn(1);

            // When
            deepQaService.submitAnswer(userId, req);

            // Then
            verify(deepQaAnswerMapper).insert(argThat(answer ->
                    answer.getQuestionId().equals(10L) &&
                    answer.getUserId().equals(userId) &&
                    answer.getAnswerText().equals("信任和包容") &&
                    answer.getIsRevealed() == 0
            ));
        }

        @Test
        @DisplayName("提交答案-已回答过应抛IllegalStateException")
        void submitAnswer_alreadyAnswered_throw() {
            // Given
            DeepQaDTO.SubmitAnswerReq req = new DeepQaDTO.SubmitAnswerReq();
            req.setQuestionId(10L);
            req.setAnswerText("信任");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(deepQaAnswerMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class,
                    () -> deepQaService.submitAnswer(userId, req));
            assertEquals("该问题已回答过", ex.getMessage());
        }

        @Test
        @DisplayName("提交答案-未绑定情侣应抛异常")
        void submitAnswer_notBound_throw() {
            // Given
            user.setCoupleId(null);
            DeepQaDTO.SubmitAnswerReq req = new DeepQaDTO.SubmitAnswerReq();
            req.setQuestionId(10L);
            req.setAnswerText("信任");

            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.submitAnswer(userId, req));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }

        @Test
        @DisplayName("提交答案-进度更新冲突时重试")
        void submitAnswer_progressConflict_retry() {
            // Given
            DeepQaDTO.SubmitAnswerReq req = new DeepQaDTO.SubmitAnswerReq();
            req.setQuestionId(10L);
            req.setAnswerText("信任");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(deepQaAnswerMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(deepQaAnswerMapper.insert(any(DeepQaAnswer.class))).thenReturn(1);
            // First update returns 0 (conflict), retry progress
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(7L);
            when(coupleQaProgressMapper.update(any(), any(LambdaUpdateWrapper.class))).thenReturn(0);

            // When
            deepQaService.submitAnswer(userId, req);

            // Then - should retry with direct SQL update
            verify(coupleQaProgressMapper, times(2)).update(any(), any(LambdaUpdateWrapper.class));
        }
    }

    @Nested
    @DisplayName("揭晓答案")
    class RevealAnswer {

        @Test
        @DisplayName("揭晓答案-成功")
        void revealAnswer_success() {
            // Given
            DeepQaAnswer myAnswer = new DeepQaAnswer();
            myAnswer.setId(1L);
            myAnswer.setQuestionId(10L);
            myAnswer.setUserId(userId);
            myAnswer.setIsRevealed(0);

            DeepQaAnswer partnerAnswerObj = new DeepQaAnswer();
            partnerAnswerObj.setId(2L);
            partnerAnswerObj.setQuestionId(10L);
            partnerAnswerObj.setUserId(partnerId);
            partnerAnswerObj.setIsRevealed(0);

            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);
            when(deepQaAnswerMapper.selectCount(argThat(w -> {
                // We need to distinguish between the two selectCount calls
                return true;
            }))).thenReturn(1L);
            when(deepQaAnswerMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(myAnswer, partnerAnswerObj));
            when(deepQuestionMapper.selectById(10L)).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            DeepQaDTO result = deepQaService.revealAnswer(userId, 10L);

            // Then
            assertNotNull(result);
            verify(deepQaAnswerMapper, times(2)).updateById(any(DeepQaAnswer.class));
        }

        @Test
        @DisplayName("揭晓答案-双方未都回答应抛IllegalStateException")
        void revealAnswer_notBothAnswered_throw() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);
            // My answer exists, partner's doesn't
            when(deepQaAnswerMapper.selectCount(any(LambdaQueryWrapper.class)))
                    .thenReturn(1L)   // my answer
                    .thenReturn(0L);  // partner answer

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class,
                    () -> deepQaService.revealAnswer(userId, 10L));
            assertEquals("双方都回答后才能揭晓", ex.getMessage());
        }

        @Test
        @DisplayName("揭晓答案-未绑定情侣应抛异常")
        void revealAnswer_notBound_throw() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.revealAnswer(userId, 10L));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("获取进度")
    class GetProgress {

        @Test
        @DisplayName("获取进度-成功")
        void getProgress_success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(50L);

            // When
            DeepQaDTO.ProgressInfo result = deepQaService.getProgress(userId);

            // Then
            assertNotNull(result);
            assertEquals(1, result.getCurrentWeek());
            assertEquals(1, result.getCurrentQuestion());
            assertEquals(0, result.getTotalCompleted());
            assertEquals(50, result.getTotalQuestions());
        }

        @Test
        @DisplayName("获取进度-进度不存在时自动创建")
        void getProgress_autoCreate() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleQaProgressMapper.insert(any(CoupleQaProgress.class))).thenReturn(1);
            when(deepQuestionMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(50L);

            // When
            DeepQaDTO.ProgressInfo result = deepQaService.getProgress(userId);

            // Then
            assertNotNull(result);
            assertEquals(1, result.getCurrentWeek());
            assertEquals(1, result.getCurrentQuestion());
        }

        @Test
        @DisplayName("获取进度-未绑定情侣应抛异常")
        void getProgress_notBound_throw() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.getProgress(userId));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("获取历史答案")
    class GetHistoryAnswers {

        @Test
        @DisplayName("获取历史答案-成功")
        void getHistoryAnswers_success() {
            // Given
            DeepQaAnswer answer = new DeepQaAnswer();
            answer.setId(1L);
            answer.setQuestionId(10L);
            answer.setCoupleId(coupleId);
            answer.setUserId(userId);
            answer.setIsRevealed(1);
            answer.setRevealTime(LocalDateTime.now());

            when(userMapper.selectById(userId)).thenReturn(user);
            when(deepQaAnswerMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(answer));
            when(deepQuestionMapper.selectById(10L)).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            List<DeepQaDTO> result = deepQaService.getHistoryAnswers(userId, 10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }

        @Test
        @DisplayName("获取历史答案-未绑定情侣应抛异常")
        void getHistoryAnswers_notBound_throw() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.getHistoryAnswers(userId, 10));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("跳过问题")
    class SkipQuestion {

        @Test
        @DisplayName("跳过问题-成功")
        void skipQuestion_success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(coupleQaProgressMapper.updateById(any(CoupleQaProgress.class))).thenReturn(1);

            // When
            deepQaService.skipQuestion(userId);

            // Then
            verify(coupleQaProgressMapper).updateById(argThat(p ->
                    p.getCurrentQuestion() == 2
            ));
        }

        @Test
        @DisplayName("跳过问题-未绑定情侣应抛异常")
        void skipQuestion_notBound_throw() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> deepQaService.skipQuestion(userId));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("初始化题目库")
    class InitQuestionBank {

        @Test
        @DisplayName("初始化题目库-题库为空时初始化")
        void initQuestionBank_empty() {
            // Given
            when(deepQuestionMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(deepQuestionMapper.insert(any(DeepQuestion.class))).thenReturn(1);

            // When
            deepQaService.initQuestionBank();

            // Then
            verify(deepQuestionMapper, times(10)).insert(any(DeepQuestion.class));
        }

        @Test
        @DisplayName("初始化题目库-题库已存在不重复初始化")
        void initQuestionBank_alreadyExists() {
            // Given
            when(deepQuestionMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(10L);

            // When
            deepQaService.initQuestionBank();

            // Then
            verify(deepQuestionMapper, never()).insert(any(DeepQuestion.class));
        }
    }

    @Nested
    @DisplayName("分类名称映射")
    class CategoryNameMapping {

        @Test
        @DisplayName("getCurrentQuestion分类名称正确映射")
        void categoryName_correctMapping() {
            // Given - category = "future"
            question.setCategory("future");
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            DeepQaDTO result = deepQaService.getCurrentQuestion(userId);

            // Then
            assertEquals("未来", result.getCategoryName());
        }

        @Test
        @DisplayName("分类名称-values映射为价值观")
        void categoryName_values() {
            // Given
            question.setCategory("values");
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            DeepQaDTO result = deepQaService.getCurrentQuestion(userId);

            // Then
            assertEquals("价值观", result.getCategoryName());
        }

        @Test
        @DisplayName("分类名称-未知分类原样返回")
        void categoryName_unknown() {
            // Given
            question.setCategory("hobbies");
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleQaProgressMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(progress);
            when(deepQuestionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(question);
            when(deepQaAnswerMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            DeepQaDTO result = deepQaService.getCurrentQuestion(userId);

            // Then
            assertEquals("hobbies", result.getCategoryName());
        }
    }
}
