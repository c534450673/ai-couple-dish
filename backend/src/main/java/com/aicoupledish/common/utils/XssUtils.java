package com.aicoupledish.common.utils;

import cn.hutool.core.text.CharSequenceUtil;
import cn.hutool.core.util.EscapeUtil;

/**
 * XSS防护工具类
 */
public class XssUtils {

    /**
     * 清理HTML内容 - 基础模式
     * 转义HTML特殊字符
     *
     * @param content 原始内容
     * @return 清理后的安全内容
     */
    public static String cleanBasic(String content) {
        if (content == null) {
            return null;
        }
        return EscapeUtil.escapeHtml4(content);
    }

    /**
     * 清理HTML内容 - 宽松模式
     * 转义HTML特殊字符（与基础模式相同）
     *
     * @param content 原始内容
     * @return 清理后的安全内容
     */
    public static String cleanRelaxed(String content) {
        if (content == null) {
            return null;
        }
        return EscapeUtil.escapeHtml4(content);
    }

    /**
     * 清理HTML内容 - 严格模式
     * 移除所有HTML标签，仅保留纯文本
     *
     * @param content 原始内容
     * @return 清理后的纯文本
     */
    public static String cleanStrict(String content) {
        if (content == null) {
            return null;
        }
        // 先移除HTML标签，再转义
        String text = content.replaceAll("<[^>]*>", "");
        return EscapeUtil.escapeHtml4(text);
    }

    /**
     * 清理用户输入 - 用于评论、笔记等
     * 使用基础模式，允许简单格式
     *
     * @param content 用户输入内容
     * @return 安全的内容
     */
    public static String sanitizeUserInput(String content) {
        return cleanBasic(content);
    }

    /**
     * 清理富文本内容 - 用于文章、菜谱步骤等
     * 使用宽松模式，允许更多格式
     *
     * @param content 富文本内容
     * @return 安全的内容
     */
    public static String sanitizeRichText(String content) {
        return cleanRelaxed(content);
    }

    /**
     * 清理纯文本输入 - 用于标题、名称等
     * 使用严格模式，不允许任何HTML
     *
     * @param content 文本内容
     * @return 安全的纯文本
     */
    public static String sanitizePlainText(String content) {
        if (content == null) {
            return null;
        }
        // 移除所有HTML标签
        String text = content.replaceAll("<[^>]*>", "");
        // 转义HTML特殊字符
        return EscapeUtil.escapeHtml4(text);
    }
}
