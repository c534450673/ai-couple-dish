package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.HeartMomentMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.HeartMoment;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.HeartMomentDTO;
import com.aicoupledish.domain.req.HeartMomentReq;
import com.aicoupledish.service.impl.HeartMomentServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 心动时刻服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("心动时刻服务测试")
class HeartMomentServiceTest {

    @Mock
    private HeartMomentMapper heartMomentMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private HeartMomentServiceImpl heartMomentService;

    private User testUser;
    private User partnerUser;
    private Couple testCouple;
    private HeartMoment testMoment;
    private HeartMomentReq momentReq;

    @BeforeEach
    void setUp() {
        testUser = new User();
        testUser.setId(1L);
        testUser.setOpenid("test_openid_001");
        testUser.setNickName("用户1");
        testUser.setAvatarUrl("https://example.com/avatar1.jpg");
        testUser.setStatus(0);
        testUser.setCoupleId(1L);
        testUser.setCreateTime(LocalDateTime.now());

        partnerUser = new User();
        partnerUser.setId(2L);
        partnerUser.setOpenid("test_openid_002");
        partnerUser.setNickName("用户2");
        partnerUser.setStatus(0);

        testCouple = new Couple();
        testCouple.setId(1L);
        testCouple.setUser1Id(1L);
        testCouple.setUser2Id(2L);
        testCouple.setStatus(1);

        momentReq = new HeartMomentReq();
        momentReq.setMomentType("text");
        momentReq.setContent("今天的心情真好");
    }

}
