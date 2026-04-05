package com.aicoupledish.common.enums;

import lombok.Getter;

/**
 * 业务异常
 */
@Getter
public class BusinessException extends RuntimeException {

    private final Integer code;

    public BusinessException(Integer code, String message) {
        super(message);
        this.code = code;
    }

    public BusinessException(String message) {
        super(message);
        this.code = 9999;
    }

    // 用户相关 1000-1999
    public static final BusinessException USER_NOT_FOUND = new BusinessException(1001, "用户不存在");
    public static final BusinessException USER_ALREADY_EXISTS = new BusinessException(1002, "用户已存在");
    public static final BusinessException USER_NOT_LOGGED_IN = new BusinessException(1003, "用户未登录");

    // 情侣相关 2000-2999
    public static final BusinessException COUPLE_NOT_FOUND = new BusinessException(2001, "情侣关系不存在");
    public static final BusinessException COUPLE_ALREADY_BIND = new BusinessException(2002, "已经绑定过情侣关系");
    public static final BusinessException COUPLE_CODE_INVALID = new BusinessException(2003, "情侣码无效或已过期");
    public static final BusinessException COUPLE_CODE_EXPIRED = new BusinessException(2004, "情侣码已过期");
    public static final BusinessException COUPLE_BIND_CONFLICT = new BusinessException(2005, "绑定冲突，请刷新重试");
    public static final BusinessException COUPLE_NOT_BIND = new BusinessException(2006, "未绑定情侣关系");
    public static final BusinessException COUPLE_CANNOT_UNBIND = new BusinessException(2007, "需要双方确认才能解绑");
    public static final BusinessException COUPLE_UNBIND_COOLDOWN = new BusinessException(2008, "解绑后需等待24小时才能重新绑定");

    // 菜单相关 3000-3999
    public static final BusinessException MENU_NOT_FOUND = new BusinessException(3001, "菜单不存在");
    public static final BusinessException MENU_NOT_PERMISSION = new BusinessException(3002, "无权操作此菜单");
    public static final BusinessException MENU_STATUS_INVALID = new BusinessException(3003, "菜单状态无效");

    // 笔记相关 4000-4999
    public static final BusinessException NOTE_NOT_FOUND = new BusinessException(4001, "笔记不存在");
    public static final BusinessException NOTE_NOT_PERMISSION = new BusinessException(4002, "无权操作此笔记");

    // 纪念日相关 5000-5999
    public static final BusinessException ANNIVERSARY_NOT_FOUND = new BusinessException(5001, "纪念日不存在");
    public static final BusinessException ANNIVERSARY_ALREADY_EXISTS = new BusinessException(5002, "该日期的纪念日已存在");
    public static final BusinessException ANNIVERSARY_CANNOT_DELETE = new BusinessException(5003, "恋爱日不能删除");

    // 投喂相关 6000-6999
    public static final BusinessException FEED_NOT_FOUND = new BusinessException(6001, "投喂记录不存在");
    public static final BusinessException FEED_ALREADY_SENT = new BusinessException(6002, "今日已发送投喂");
    public static final BusinessException FEED_EXPIRED = new BusinessException(6003, "投喂已过期");
    public static final BusinessException FEED_CANNOT_ACCEPT = new BusinessException(6004, "无法接受此投喂");

    // 订单相关 7000-7999
    public static final BusinessException ORDER_NOT_FOUND = new BusinessException(7001, "订单不存在");
    public static final BusinessException ORDER_STATUS_INVALID = new BusinessException(7002, "订单状态无效");
    public static final BusinessException ORDER_CANNOT_CANCEL = new BusinessException(7003, "订单无法取消");

    // 菜谱相关 8000-8999
    public static final BusinessException RECIPE_NOT_FOUND = new BusinessException(8001, "菜谱不存在");
    public static final BusinessException RECIPE_NOT_PERMISSION = new BusinessException(8002, "无权操作此菜谱");
    public static final BusinessException RECIPE_STATUS_INVALID = new BusinessException(8003, "菜谱状态无效");

    // 心愿相关 8500-8599
    public static final BusinessException WISH_NOT_FOUND = new BusinessException(8501, "心愿不存在");
    public static final BusinessException WISH_NOT_PERMISSION = new BusinessException(8502, "无权操作此心愿");

    // 问候相关 8600-8699
    public static final BusinessException GREETING_NOT_FOUND = new BusinessException(8601, "问候记录不存在");
    public static final BusinessException GREETING_ALREADY_SENT = new BusinessException(8602, "今日已发送过该问候");
    public static final BusinessException GREETING_NOT_PERMISSION = new BusinessException(8603, "无权操作此问候");

    // 爱心树相关 8700-8799
    public static final BusinessException TREE_NOT_FOUND = new BusinessException(8701, "爱心树不存在");
    public static final BusinessException TREE_SKIN_LOCKED = new BusinessException(8702, "该皮肤尚未解锁");

    // 每日任务相关 8800-8899
    public static final BusinessException TASK_NOT_FOUND = new BusinessException(8801, "任务不存在");
    public static final BusinessException TASK_EXPIRED = new BusinessException(8802, "任务已过期");
    public static final BusinessException TASK_NOT_COMPLETED = new BusinessException(8803, "任务尚未完成");
    public static final BusinessException TASK_REWARD_CLAIMED = new BusinessException(8804, "奖励已领取");

    // 海报相关 8900-8999
    public static final BusinessException POSTER_NOT_FOUND = new BusinessException(8901, "海报不存在");
    public static final BusinessException POSTER_TEMPLATE_NOT_FOUND = new BusinessException(8902, "海报模板不存在");
    public static final BusinessException POSTER_NOT_PERMISSION = new BusinessException(8903, "无权操作此海报");

    // 邀请相关 8950-8999
    public static final BusinessException INVITE_CODE_NOT_FOUND = new BusinessException(8951, "邀请码不存在");
    public static final BusinessException INVITE_CODE_USED = new BusinessException(8952, "已使用过邀请码");
    public static final BusinessException INVITE_CODE_SELF = new BusinessException(8953, "不能使用自己的邀请码");

    // 系统相关 9000-9999
    public static final BusinessException PARAM_INVALID = new BusinessException(9001, "参数无效");
    public static final BusinessException FILE_UPLOAD_FAILED = new BusinessException(9002, "文件上传失败");
    public static final BusinessException SMS_CODE_ERROR = new BusinessException(9003, "验证码错误");
    public static final BusinessException SMS_CODE_EXPIRED = new BusinessException(9004, "验证码已过期");
    public static final BusinessException OPERATION_TOO_FREQUENT = new BusinessException(9005, "操作过于频繁，请稍后重试");
}