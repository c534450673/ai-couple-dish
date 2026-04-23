package com.aicoupledish.controller;

import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.CoupleCodeDTO;
import com.aicoupledish.domain.dto.CoupleHomeDTO;
import com.aicoupledish.domain.dto.CoupleInfoDTO;
import com.aicoupledish.domain.req.BindCoupleReq;
import com.aicoupledish.domain.req.GenerateCodeReq;
import com.aicoupledish.domain.req.UnbindReq;
import com.aicoupledish.service.CoupleService;
import com.aicoupledish.service.UserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;

/**
 * 情侣控制器
 */
@Api(tags = "情侣模块")
@RestController
@RequestMapping("/couple")
@RequiredArgsConstructor
public class CoupleController extends BaseAuthController {

    private final CoupleService coupleService;
    private final UserService userService;
    private final com.aicoupledish.common.utils.JwtUtils jwtUtils;

    private final HttpServletRequest request;

    @ApiOperation("生成情侣码")
    @PostMapping("/generateCode")
    public Result<String> generateCoupleCode(@RequestBody(required = false) GenerateCodeReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);

        // 兼容前端不传请求体的场景，默认使用当天作为恋爱开始日期
        if (req == null || req.getLoveStartDate() == null || req.getLoveStartDate().trim().isEmpty()) {
            req = new GenerateCodeReq();
            req.setLoveStartDate(java.time.LocalDate.now().toString());
        }

        String coupleCode = coupleService.generateCoupleCode(userId, req);
        return Result.success("情侣码生成成功", coupleCode);
    }

    @ApiOperation("绑定情侣")
    @PostMapping("/bind")
    public Result<CoupleInfoDTO> bindCouple(@Valid @RequestBody BindCoupleReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleInfoDTO coupleInfo = coupleService.bindCouple(userId, req);
        return Result.success("绑定成功", coupleInfo);
    }

    @ApiOperation("获取情侣信息")
    @GetMapping("/info")
    public Result<CoupleInfoDTO> getCoupleInfo() {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleInfoDTO coupleInfo = coupleService.getCoupleInfo(userId);
        return Result.success(coupleInfo);
    }

    @ApiOperation("获取情侣主页")
    @GetMapping("/home")
    public Result<CoupleHomeDTO> getCoupleHome() {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleHomeDTO home = coupleService.getCoupleHome(userId);
        return Result.success(home);
    }

    @ApiOperation("申请解绑")
    @PostMapping("/unbind/apply")
    public Result<Void> applyUnbind(@RequestBody(required = false) UnbindReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        coupleService.applyUnbind(userId, req != null ? req : new UnbindReq());
        return Result.success();
    }

    @ApiOperation("确认解绑")
    @PostMapping("/unbind/confirm")
    public Result<Void> confirmUnbind(@RequestParam Long coupleId) {
        Long userId = getCurrentUserId(request, jwtUtils);
        coupleService.confirmUnbind(userId, coupleId);
        return Result.success();
    }

    @ApiOperation("拒绝解绑")
    @PostMapping("/unbind/reject")
    public Result<Void> rejectUnbind(@RequestParam Long coupleId) {
        Long userId = getCurrentUserId(request, jwtUtils);
        coupleService.rejectUnbind(userId, coupleId);
        return Result.success();
    }

    @ApiOperation("验证情侣码")
    @GetMapping("/validateCode")
    public Result<Boolean> validateCoupleCode(@RequestParam String coupleCode) {
        boolean valid = coupleService.validateCoupleCode(coupleCode);
        return Result.success(valid);
    }

    @ApiOperation("获取恋爱计时")
    @GetMapping("/loveTimer")
    public Result<CoupleHomeDTO> getLoveTimer() {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleHomeDTO timer = coupleService.getLoveTimer(userId);
        return Result.success(timer);
    }

    @ApiOperation("检查可恢复的情侣数据")
    @GetMapping("/recoverable")
    public Result<CoupleInfoDTO> checkRecoverableData() {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleInfoDTO data = coupleService.checkRecoverableData(userId);
        return Result.success(data);
    }

    @ApiOperation("恢复情侣数据")
    @PostMapping("/recover")
    public Result<CoupleInfoDTO> recoverCoupleData(@RequestParam Long recordId) {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleInfoDTO coupleInfo = coupleService.recoverCoupleData(userId, recordId);
        return Result.success("数据恢复成功", coupleInfo);
    }

    @ApiOperation("获取当前情侣码信息")
    @GetMapping("/codeInfo")
    public Result<CoupleCodeDTO> getCoupleCodeInfo() {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleCodeDTO codeInfo = coupleService.getCoupleCodeInfo(userId);
        return Result.success(codeInfo);
    }

    @ApiOperation("刷新情侣码")
    @PostMapping("/refreshCode")
    public Result<String> refreshCoupleCode() {
        Long userId = getCurrentUserId(request, jwtUtils);
        String newCode = coupleService.refreshCoupleCode(userId);
        return Result.success("情侣码已刷新", newCode);
    }

}