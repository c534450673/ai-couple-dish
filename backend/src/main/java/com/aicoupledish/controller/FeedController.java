package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.FeedDTO;
import com.aicoupledish.domain.dto.TodayFeedDTO;
import com.aicoupledish.domain.req.SendFeedReq;
import com.aicoupledish.service.FeedService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 投喂控制器
 */
@Api(tags = "投喂模块")
@RestController
@RequestMapping("/feed")
@RequiredArgsConstructor
public class FeedController extends BaseAuthController {

    private final FeedService feedService;
    private final JwtUtils jwtUtils;

    private final HttpServletRequest request;

    @ApiOperation("获取今日投喂状态")
    @GetMapping("/today")
    public Result<TodayFeedDTO> getTodayFeedStatus() {
        Long userId = getCurrentUserId(request, jwtUtils);
        TodayFeedDTO status = feedService.getTodayFeedStatus(userId);
        return Result.success(status);
    }

    @ApiOperation("发送投喂")
    @PostMapping("/send")
    public Result<Long> sendFeed(@Valid @RequestBody SendFeedReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        Long feedId = feedService.sendFeed(userId, req);
        return Result.success("投喂发送成功", feedId);
    }

    @ApiOperation("获取收到的投喂列表")
    @GetMapping("/received")
    public Result<List<FeedDTO>> getReceivedFeeds() {
        Long userId = getCurrentUserId();
        List<FeedDTO> list = feedService.getReceivedFeeds(userId);
        return Result.success(list);
    }

    @ApiOperation("获取发出的投喂列表")
    @GetMapping("/sent")
    public Result<List<FeedDTO>> getSentFeeds() {
        Long userId = getCurrentUserId();
        List<FeedDTO> list = feedService.getSentFeeds(userId);
        return Result.success(list);
    }

    @ApiOperation("接受投喂")
    @PostMapping("/accept/{id}")
    public Result<Void> acceptFeed(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        feedService.acceptFeed(userId, id);
        return Result.success();
    }

    @ApiOperation("拒绝投喂")
    @PostMapping("/reject/{id}")
    public Result<Void> rejectFeed(
            @PathVariable Long id,
            @RequestParam(required = false) String reason) {
        Long userId = getCurrentUserId();
        feedService.rejectFeed(userId, id, reason);
        return Result.success();
    }

}