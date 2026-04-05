package com.aicoupledish;

import com.aicoupledish.common.utils.SensitiveDataUtils;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 敏感数据处理工具测试
 */
@DisplayName("敏感数据处理工具测试")
class SensitiveDataUtilsTest {

    @Test
    @DisplayName("手机号脱敏-正常手机号")
    void maskPhone_Normal() {
        String phone = "13812345678";
        String masked = SensitiveDataUtils.maskPhone(phone);
        assertEquals("138****5678", masked);
    }

    @Test
    @DisplayName("手机号脱敏-短号码")
    void maskPhone_Short() {
        String phone = "138";
        String masked = SensitiveDataUtils.maskPhone(phone);
        assertEquals("138", masked);
    }

    @Test
    @DisplayName("手机号脱敏-null")
    void maskPhone_Null() {
        String masked = SensitiveDataUtils.maskPhone(null);
        assertNull(masked);
    }

    @Test
    @DisplayName("身份证号脱敏-正常身份证")
    void maskIdCard_Normal() {
        String idCard = "110101199001011234";
        String masked = SensitiveDataUtils.maskIdCard(idCard);
        assertEquals("110101********1234", masked);
    }

    @Test
    @DisplayName("身份证号脱敏-短号码")
    void maskIdCard_Short() {
        String idCard = "12345";
        String masked = SensitiveDataUtils.maskIdCard(idCard);
        assertEquals("12345", masked);
    }

    @Test
    @DisplayName("银行卡号脱敏-正常银行卡")
    void maskBankCard_Normal() {
        String bankCard = "6222021234567890123";
        String masked = SensitiveDataUtils.maskBankCard(bankCard);
        assertTrue(masked.startsWith("6222"));
        assertTrue(masked.endsWith("123"));
        assertTrue(masked.contains("****"));
    }

    @Test
    @DisplayName("邮箱脱敏-正常邮箱")
    void maskEmail_Normal() {
        String email = "example@test.com";
        String masked = SensitiveDataUtils.maskEmail(email);
        assertEquals("e****@test.com", masked);
    }

    @Test
    @DisplayName("邮箱脱敏-无@符号")
    void maskEmail_NoAt() {
        String email = "exampletest.com";
        String masked = SensitiveDataUtils.maskEmail(email);
        assertEquals("exampletest.com", masked);
    }

    @Test
    @DisplayName("姓名脱敏-两个字")
    void maskName_TwoChars() {
        String name = "张三";
        String masked = SensitiveDataUtils.maskName(name);
        assertEquals("张*", masked);
    }

    @Test
    @DisplayName("姓名脱敏-三个字")
    void maskName_ThreeChars() {
        String name = "王小明";
        String masked = SensitiveDataUtils.maskName(name);
        assertEquals("王**", masked);
    }

    @Test
    @DisplayName("地址脱敏-正常地址")
    void maskAddress_Normal() {
        String address = "北京市朝阳区xxx街道xxx号";
        String masked = SensitiveDataUtils.maskAddress(address);
        assertEquals("北京市朝阳区***", masked);
    }

    @Test
    @DisplayName("地址脱敏-短地址")
    void maskAddress_Short() {
        String address = "北京";
        String masked = SensitiveDataUtils.maskAddress(address);
        assertEquals("北京", masked);
    }
}
