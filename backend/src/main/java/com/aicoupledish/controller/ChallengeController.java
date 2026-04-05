package com.aicoupledish.controller;

import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.ChallengeDTO;
import com.aicoupledish.domain.dto.CheckinRecordDTO;
import com.aicoupledish.domain.req.CheckinReq;
import com.aicoupledish.domain.req.CreateChallengeReq;
import com.aicoupledish.service.ChallengeService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 打卡挑战控制器
 */
@Api(tags = "打卡挑战")
@RestController
@RequestMapping("/challenge")
@RequiredArgsConstructor
public class ChallengeController {

    private final ChallengeService challengeService;

    @ApiOperation("创建挑战")
    @PostMapping("/create")
    public Result<Long> createChallenge(
            @RequestAttribute("userId") Long userId,
            @Validated @RequestBody CreateChallengeReq req) {
        Long challengeId = challengeService.createChallenge(userId, req);
        return Result.success(challengeId);
    }

    @ApiOperation("接受挑战")
    @PostMapping("/accept/{challengeId}")
    public Result<Void> acceptChallenge(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long challengeId) {
        challengeService.acceptChallenge(userId, challengeId);
        return Result.success("接受成功");
    }

    @ApiOperation("拒绝挑战")
    @PostMapping("/reject/{challengeId}")
    public Result<Void> rejectChallenge(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long challengeId) {
        challengeService.rejectChallenge(userId, challengeId);
        return Result.success("已拒绝");
    }

    @ApiOperation("取消挑战")
    @PostMapping("/cancel/{challengeId}")
    public Result<Void> cancelChallenge(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long challengeId) {
        challengeService.cancelChallenge(userId, challengeId);
        return Result.success("已取消");
    }

    @ApiOperation("打卡")
    @PostMapping("/checkin")
    public Result<CheckinRecordDTO> checkin(
            @RequestAttribute("userId") Long userId,
            @Validated @RequestBody CheckinReq req) {
        CheckinRecordDTO dto = challengeService.checkin(userId, req);
        return Result.success(dto);
    }

    @ApiOperation("获取挑战详情")
    @GetMapping("/detail/{challengeId}")
    public Result<ChallengeDTO> getChallengeDetail(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long challengeId) {
        ChallengeDTO dto = challengeService.getChallengeDetail(userId, challengeId);
        return Result.success(dto);
    }

    @ApiOperation("获取挑战列表")
    @GetMapping("/list")
    public Result<List<ChallengeDTO>> getChallengeList(
            @RequestAttribute("userId") Long userId,
            @RequestParam(required = false) @ApiParam("状态：0-进行中 1-已完成 2-已失败 3-已取消") Integer status) {
        List<ChallengeDTO> list = challengeService.getChallengeList(userId, status);
        return Result.success(list);
    }

    @ApiOperation("获取打卡记录")
    @GetMapping("/checkin-records/{challengeId}")
    public Result<Page<CheckinRecordDTO>> getCheckinRecords(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long challengeId,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<CheckinRecordDTO> page = challengeService.getCheckinRecords(userId, challengeId, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("获取待处理的挑战")
    @GetMapping("/pending")
    public Result<List<ChallengeDTO>> getPendingChallenges(
            @RequestAttribute("userId") Long userId) {
        List<ChallengeDTO> list = challengeService.getPendingChallenges(userId);
        return Result.success(list);
    }
}
