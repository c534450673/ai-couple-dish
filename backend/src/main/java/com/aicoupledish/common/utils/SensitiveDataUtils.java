package com.aicoupledish.common.utils;

/**
 * 敏感数据处理工具类
 */
public class SensitiveDataUtils {

    /**
     * 手机号脱敏
     * 13812345678 -> 138****5678
     */
    public static String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    /**
     * 身份证号脱敏
     * 110101199001011234 -> 110101********1234
     */
    public static String maskIdCard(String idCard) {
        if (idCard == null || idCard.length() < 8) {
            return idCard;
        }
        return idCard.substring(0, 6) + "********" + idCard.substring(idCard.length() - 4);
    }

    /**
     * 银行卡号脱敏
     * 6222021234567890123 -> 6222 **** **** 123
     */
    public static String maskBankCard(String bankCard) {
        if (bankCard == null || bankCard.length() < 8) {
            return bankCard;
        }
        return bankCard.substring(0, 4) + " **** **** " + bankCard.substring(bankCard.length() - 3);
    }

    /**
     * 邮箱脱敏
     * example@test.com -> e****@test.com
     */
    public static String maskEmail(String email) {
        if (email == null || !email.contains("@")) {
            return email;
        }
        int atIndex = email.indexOf("@");
        if (atIndex <= 1) {
            return email;
        }
        return email.charAt(0) + "****" + email.substring(atIndex);
    }

    /**
     * 姓名脱敏
     * 张三 -> 张*
     * 王小明 -> 王**
     */
    public static String maskName(String name) {
        if (name == null || name.length() <= 1) {
            return name;
        }
        return name.charAt(0) + "*".repeat(name.length() - 1);
    }

    /**
     * 地址脱敏
     * 北京市朝阳区xxx街道xxx号 -> 北京市朝阳区***
     */
    public static String maskAddress(String address) {
        if (address == null || address.length() <= 6) {
            return address;
        }
        return address.substring(0, 6) + "***";
    }
}
