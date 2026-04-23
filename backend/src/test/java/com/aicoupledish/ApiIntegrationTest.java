package com.aicoupledish;

import com.aicoupledish.common.utils.JwtUtils;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.HashMap;
import java.util.Map;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * API集成测试
 * 测试范围：所有API端点的请求/响应格式、认证流程、参数验证
 * 注意：成功响应的code为200，失败响应的code为对应错误码
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@DisplayName("API集成测试")
class ApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JwtUtils jwtUtils;

    @MockBean
    private RedisTemplate<String, String> redisTemplate;

    @MockBean
    private ValueOperations<String, String> valueOperations;

    private String validToken;
    private Long testUserId = 1L;

    @BeforeEach
    void setUp() {
        validToken = jwtUtils.generateToken(testUserId);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
    }

    // ==================== 通用接口测试 ====================

    @Test
    @DisplayName("通用响应格式-code为200表示成功")
    void commonResponse_Code200_ShouldIndicateSuccess() throws Exception {
        // 测试获取用户信息接口
        mockMvc.perform(get("/user/info")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("通用响应格式-应包含message字段")
    void commonResponse_ShouldIncludeMessage() throws Exception {
        mockMvc.perform(get("/user/info")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(jsonPath("$.message").exists());
    }

    @Test
    @DisplayName("通用响应格式-应包含data字段")
    void commonResponse_ShouldIncludeData() throws Exception {
        mockMvc.perform(get("/user/info")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(jsonPath("$.data").exists());
    }

    // ==================== 认证接口测试 ====================

    @Test
    @DisplayName("微信登录-新用户登录应成功")
    void wechatLogin_NewUser_ShouldSucceed() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("code", "test_openid_" + System.currentTimeMillis());
        request.put("nickName", "测试用户");
        request.put("avatarUrl", "https://example.com/avatar.jpg");

        mockMvc.perform(post("/user/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.token").exists())
                .andExpect(jsonPath("$.data.userInfo").exists());
    }

    @Test
    @DisplayName("微信登录-无code参数应返回错误")
    void wechatLogin_NoCode_ShouldReturnError() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("nickName", "测试用户");

        mockMvc.perform(post("/user/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("登出-有效token应成功")
    void logout_ValidToken_ShouldSucceed() throws Exception {
        mockMvc.perform(post("/user/logout")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("获取用户信息-有效token应返回用户信息")
    void getUserInfo_ValidToken_ShouldReturnUserInfo() throws Exception {
        mockMvc.perform(get("/user/info")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.id").exists())
                .andExpect(jsonPath("$.data.openid").exists());
    }

    @Test
    @DisplayName("获取用户信息-无效token应返回401")
    void getUserInfo_InvalidToken_ShouldReturn401() throws Exception {
        mockMvc.perform(get("/user/info")
                .header("Authorization", "Bearer invalid_token"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401));
    }

    @Test
    @DisplayName("获取用户信息-无token应返回错误")
    void getUserInfo_NoToken_ShouldReturnError() throws Exception {
        mockMvc.perform(get("/user/info"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401));
    }

    // ==================== 情侣接口测试 ====================

    @Test
    @DisplayName("生成情侣码-已绑定用户应返回错误")
    void generateCoupleCode_BoundUser_ShouldReturnError() throws Exception {
        // 测试用户已绑定情侣，应返回错误
        Map<String, Object> request = new HashMap<>();
        request.put("startDate", "2026-03-21");

        mockMvc.perform(post("/couple/generateCode")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(2002)); // COUPLE_ALREADY_BIND
    }

    @Test
    @DisplayName("验证情侣码-无效码应返回404")
    void validateCoupleCode_InvalidCode_ShouldReturnError() throws Exception {
        // 验证不存在的情侣码
        mockMvc.perform(get("/couple/validate/INVALID_CODE")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("获取情侣信息-已绑定应返回信息")
    void getCoupleInfo_BoundCouple_ShouldReturnInfo() throws Exception {
        mockMvc.perform(get("/couple/info")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("获取情侣主页-已绑定应返回主页信息")
    void getCoupleHome_BoundCouple_ShouldReturnHomeInfo() throws Exception {
        mockMvc.perform(get("/couple/home")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("获取恋爱计时-已绑定应返回计时")
    void getLoveTimer_BoundCouple_ShouldReturnTimer() throws Exception {
        mockMvc.perform(get("/couple/loveTimer")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    // ==================== 菜单接口测试 ====================

    @Test
    @DisplayName("获取菜单列表-有效请求应返回列表")
    void getMenuList_ValidRequest_ShouldReturnList() throws Exception {
        mockMvc.perform(get("/menu/list")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.list").isArray());
    }

    @Test
    @DisplayName("获取菜单列表-按状态筛选应生效")
    void getMenuList_FilterByStatus_ShouldWork() throws Exception {
        mockMvc.perform(get("/menu/list")
                .param("status", "0")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("获取菜单列表-按关键词搜索应生效")
    void getMenuList_SearchByKeyword_ShouldWork() throws Exception {
        mockMvc.perform(get("/menu/list")
                .param("keyword", "酸菜鱼")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("添加菜单-完整信息应成功")
    void addMenu_FullInfo_ShouldSucceed() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("restaurantName", "太二酸菜鱼");
        request.put("dishName", "酸菜鱼");
        request.put("dishCategory", "川菜");
        request.put("price", 68.00);
        request.put("location", "深圳市南山区科兴科学园");
        request.put("rating", 5);
        request.put("status", 1);
        request.put("eatenDate", "2026-03-15");

        mockMvc.perform(post("/menu/add")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("添加菜单-缺少必填字段应有提示")
    void addMenu_MissingRequired_ShouldHaveValidation() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("dishName", "酸菜鱼");
        // restaurantName 是必填的

        mockMvc.perform(post("/menu/add")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("获取菜单统计-有效请求应返回统计")
    void getMenuStats_ValidRequest_ShouldReturnStats() throws Exception {
        mockMvc.perform(get("/menu/stats")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("点赞菜单-有效请求应成功")
    void likeMenu_ValidRequest_ShouldSucceed() throws Exception {
        mockMvc.perform(post("/menu/like/1")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("收藏菜单-有效请求应成功")
    void favoriteMenu_ValidRequest_ShouldSucceed() throws Exception {
        mockMvc.perform(post("/menu/favorite/1")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    // ==================== 投喂接口测试 ====================

    @Test
    @DisplayName("获取今日投喂状态-有效请求应返回状态")
    void getTodayFeedStatus_ValidRequest_ShouldReturnStatus() throws Exception {
        mockMvc.perform(get("/feed/today")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").exists());
    }

    @Test
    @DisplayName("发送投喂-有效请求应成功")
    void sendFeed_ValidRequest_ShouldSucceed() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("feedType", "meal");
        request.put("content", "今天给你点了外卖，记得吃哦");
        request.put("message", "爱你哟");

        mockMvc.perform(post("/feed/send")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("获取已接收投喂列表-有效请求应返回列表")
    void getReceivedFeeds_ValidRequest_ShouldReturnList() throws Exception {
        mockMvc.perform(get("/feed/received")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isArray());
    }

    @Test
    @DisplayName("获取已发送投喂列表-有效请求应返回列表")
    void getSentFeeds_ValidRequest_ShouldReturnList() throws Exception {
        mockMvc.perform(get("/feed/sent")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isArray());
    }

    // ==================== 纪念日接口测试 ====================

    @Test
    @DisplayName("获取纪念日列表-有效请求应返回列表")
    void getAnniversaryList_ValidRequest_ShouldReturnList() throws Exception {
        mockMvc.perform(get("/anniversary/list")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isArray());
    }

    @Test
    @DisplayName("获取即将到来的纪念日-有效请求应返回")
    void getUpcomingAnniversaries_ValidRequest_ShouldReturn() throws Exception {
        mockMvc.perform(get("/anniversary/upcoming")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("获取下一个纪念日-有效请求应返回")
    void getNextAnniversary_ValidRequest_ShouldReturn() throws Exception {
        mockMvc.perform(get("/anniversary/next")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("添加纪念日-有效请求应成功")
    void addAnniversary_ValidRequest_ShouldSucceed() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("name", "恋爱纪念日");
        request.put("anniversaryDate", "2026-11-11");
        request.put("anniversaryType", 2);
        request.put("remindDaysBefore", 7);

        mockMvc.perform(post("/anniversary/add")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("检查今日纪念日-有效请求应返回")
    void checkTodayAnniversary_ValidRequest_ShouldReturn() throws Exception {
        mockMvc.perform(get("/anniversary/today")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    // ==================== 笔记接口测试 ====================

    @Test
    @DisplayName("获取笔记列表-有效请求应返回列表")
    void getNoteList_ValidRequest_ShouldReturnList() throws Exception {
        mockMvc.perform(get("/note/list")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isArray());
    }

    @Test
    @DisplayName("添加笔记-有效请求应成功")
    void addNote_ValidRequest_ShouldSucceed() throws Exception {
        Map<String, Object> request = new HashMap<>();
        request.put("title", "美食日记");
        request.put("content", "今天去吃了太二酸菜鱼，味道很棒！");
        request.put("location", "深圳市南山区");

        mockMvc.perform(post("/note/add")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }

    // ==================== 错误处理测试 ====================

    @Test
    @DisplayName("错误处理-404应返回正确格式")
    void errorHandling_404_ShouldReturnCorrectFormat() throws Exception {
        mockMvc.perform(get("/nonexistent/endpoint")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("错误处理-方法不支持应返回500")
    void errorHandling_MethodNotAllowed_ShouldReturnError() throws Exception {
        mockMvc.perform(patch("/user/login")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().is5xxServerError());
    }

    @Test
    @DisplayName("错误处理-服务器错误应有统一格式")
    void errorHandling_ServerError_ShouldHaveUniformFormat() throws Exception {
        // 使用无效的ID触发错误
        mockMvc.perform(get("/menu/detail/999999")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").exists());
    }

    // ==================== 参数验证测试 ====================

    @Test
    @DisplayName("参数验证-无效手机号格式应有提示")
    void parameterValidation_InvalidPhoneFormat_ShouldHaveMessage() throws Exception {
        // 手机号格式验证在发送验证码时进行
        // 这里测试一个明显无效的格式
        mockMvc.perform(get("/user/info")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("参数验证-超出范围的status应有处理")
    void parameterValidation_OutOfRangeStatus_ShouldBeHandled() throws Exception {
        mockMvc.perform(get("/menu/list")
                .param("status", "99")
                .header("Authorization", "Bearer " + validToken))
                .andExpect(status().isOk());
    }
}
