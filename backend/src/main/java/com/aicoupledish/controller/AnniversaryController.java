package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.AnniversaryDTO;
import com.aicoupledish.domain.req.AddAnniversaryReq;
import com.aicoupledish.domain.req.ReminderConfigReq;
import com.aicoupledish.service.AnniversaryService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 纪念日控制器
 */
@Api(tags = "纪念日模块")
@RestController
@RequestMapping("/anniversary")
@RequiredArgsConstructor
public class AnniversaryController extends BaseAuthController {

    private final AnniversaryService anniversaryService;
    private final JwtUtils jwtUtils;

    private final HttpServletRequest request;

    @ApiOperation("获取纪念日列表")
    @GetMapping("/list")
    public Result<List<AnniversaryDTO>> getAnniversaryList() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<AnniversaryDTO> list = anniversaryService.getAnniversaryList(userId);
        return Result.success(list);
    }

    @ApiOperation("获取即将到来的纪念日")
    @GetMapping("/upcoming")
    public Result<List<AnniversaryDTO>> getUpcomingAnniversaries() {
        Long userId = getCurrentUserId();
        List<AnniversaryDTO> list = anniversaryService.getUpcomingAnniversaries(userId);
        return Result.success(list);
    }

    @ApiOperation("获取下一个纪念日")
    @GetMapping("/next")
    public Result<AnniversaryDTO> getNextAnniversary() {
        Long userId = getCurrentUserId();
        AnniversaryDTO next = anniversaryService.getNextAnniversary(userId);
        return Result.success(next);
    }

    @ApiOperation("添加纪念日")
    @PostMapping("/add")
    public Result<Long> addAnniversary(@Valid @RequestBody AddAnniversaryReq req) {
        Long userId = getCurrentUserId();
        Long id = anniversaryService.addAnniversary(userId, req);
        return Result.success("纪念日添加成功", id);
    }

    @ApiOperation("更新纪念日")
    @PutMapping("/update/{id}")
    public Result<Void> updateAnniversary(@PathVariable Long id, @RequestBody AddAnniversaryReq req) {
        Long userId = getCurrentUserId();
        anniversaryService.updateAnniversary(userId, id, req);
        return Result.success();
    }

    @ApiOperation("删除纪念日")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteAnniversary(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        anniversaryService.deleteAnniversary(userId, id);
        return Result.success();
    }

    @ApiOperation("检查今日是否是纪念日")
    @GetMapping("/today")
    public Result<AnniversaryDTO> checkTodayAnniversary() {
        Long userId = getCurrentUserId();
        AnniversaryDTO today = anniversaryService.checkTodayAnniversary(userId);
        return Result.success(today);
    }

    @ApiOperation("更新提醒配置")
    @PutMapping("/reminderConfig")
    public Result<Void> updateReminderConfig(@Valid @RequestBody ReminderConfigReq req) {
        Long userId = getCurrentUserId();
        anniversaryService.updateReminderConfig(userId, req);
        return Result.success();
    }

}