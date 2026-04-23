package com.aicoupledish.controller;

import com.aicoupledish.common.annotation.RateLimit;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.LoginRespDTO;
import com.aicoupledish.domain.dto.UserInfoDTO;
import com.aicoupledish.domain.req.PhoneLoginReq;
import com.aicoupledish.domain.req.UpdateUserReq;
import com.aicoupledish.domain.req.WechatLoginReq;
import com.aicoupledish.service.UserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;

/**
 * 用户控制器
 */
@Api(tags = "用户模块")
@RestController
@RequestMapping("/user")
@RequiredArgsConstructor
public class UserController extends BaseAuthController {

    private final UserService userService;
    private final JwtUtils jwtUtils;

    @ApiOperation("微信登录（含自动注册）")
    @PostMapping("/login")
    public Result<LoginRespDTO> wechatLogin(@Valid @RequestBody WechatLoginReq req) {
        LoginRespDTO resp = userService.wechatLogin(req);
        return Result.success(resp);
    }

    @ApiOperation("手机号注册")
    @PostMapping("/register")
    @RateLimit(key = "register", time = 60, count = 5, limitType = RateLimit.LimitType.IP, message = "注册操作太频繁，请1分钟后再试")
    public Result<LoginRespDTO> registerByPhone(@Valid @RequestBody PhoneLoginReq req) {
        LoginRespDTO resp = userService.registerByPhone(req.getPhone(), req.getVerifyCode());
        return Result.success(resp);
    }

    @ApiOperation("发送验证码")
    @PostMapping("/sendCode")
    @RateLimit(key = "sendCode", time = 60, count = 1, limitType = RateLimit.LimitType.IP, message = "验证码发送太频繁，请60秒后再试")
    public Result<Void> sendVerifyCode(@RequestParam String phone) {
        userService.sendVerifyCode(phone);
        return Result.success("验证码发送成功");
    }

    @ApiOperation("手机号登录")
    @PostMapping("/phoneLogin")
    @RateLimit(key = "phoneLogin", time = 60, count = 10, limitType = RateLimit.LimitType.IP, message = "登录操作太频繁，请1分钟后再试")
    public Result<LoginRespDTO> phoneLogin(@Valid @RequestBody PhoneLoginReq req) {
        LoginRespDTO resp = userService.phoneLogin(req.getPhone(), req.getVerifyCode());
        return Result.success(resp);
    }

    @ApiOperation("获取用户信息")
    @GetMapping("/info")
    public Result<UserInfoDTO> getUserInfo(HttpServletRequest request) {
        Long userId = getCurrentUserId(request, jwtUtils);
        UserInfoDTO userInfo = userService.getUserInfo(userId);
        return Result.success(userInfo);
    }

    @ApiOperation("更新用户信息")
    @PutMapping("/update")
    public Result<Void> updateUserInfo(
            HttpServletRequest request,
            @RequestBody UpdateUserReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        userService.updateUserInfo(userId, req.getNickName(), req.getAvatarUrl());
        return Result.success();
    }

    @ApiOperation("退出登录")
    @PostMapping("/logout")
    public Result<Void> logout(HttpServletRequest request) {
        Long userId = getCurrentUserId(request, jwtUtils);
        userService.logout(userId);
        return Result.success();
    }

}
