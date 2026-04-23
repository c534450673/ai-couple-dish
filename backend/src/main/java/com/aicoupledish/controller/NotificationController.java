package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.dao.model.Notification;
import com.aicoupledish.service.NotificationService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 通知控制器
 */
@Api(tags = "通知模块")
@RestController
@RequestMapping("/notification")
@RequiredArgsConstructor
public class NotificationController extends BaseAuthController {

    private final NotificationService notificationService;
    private final JwtUtils jwtUtils;

    private final HttpServletRequest request;

    @ApiOperation("获取通知列表")
    @GetMapping("/list")
    public Result<List<Notification>> getNotificationList(
            @RequestParam(required = false) Integer type,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer pageSize) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<Notification> list = notificationService.getNotificationList(userId, type, page, pageSize);
        return Result.success(list);
    }

    @ApiOperation("获取未读通知数量")
    @GetMapping("/unreadCount")
    public Result<Integer> getUnreadCount() {
        Long userId = getCurrentUserId(request, jwtUtils);
        Integer count = notificationService.getUnreadCount(userId);
        return Result.success(count);
    }

    @ApiOperation("标记通知已读")
    @PutMapping("/read/{id}")
    public Result<Void> markAsRead(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        notificationService.markAsRead(userId, id);
        return Result.success();
    }

    @ApiOperation("标记所有通知已读")
    @PutMapping("/readAll")
    public Result<Void> markAllAsRead() {
        Long userId = getCurrentUserId(request, jwtUtils);
        notificationService.markAllAsRead(userId);
        return Result.success();
    }

    @ApiOperation("删除通知")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteNotification(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        notificationService.deleteNotification(userId, id);
        return Result.success();
    }

}