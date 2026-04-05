package com.aicoupledish.controller;

import com.aicoupledish.common.annotation.RateLimit;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.common.utils.SensitiveDataUtils;
import com.aicoupledish.domain.dto.LoginRespDTO;
import com.aicoupledish.domain.dto.UserInfoDTO;
import com.aicoupledish.domain.req.WechatLoginReq;
import com.aicoupledish.service.UserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
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

    @Autowired(required = false)
    private HttpServletRequest request;

    @ApiOperation("微信登录")
    @PostMapping("/login")
    public Result<LoginRespDTO> wechatLogin(@Valid @RequestBody WechatLoginReq req) {
        LoginRespDTO resp = userService.wechatLogin(req);
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
    public Result<LoginRespDTO> phoneLogin(@RequestParam String phone) {
        LoginRespDTO resp = userService.phoneLogin(phone);
        return Result.success(resp);
    }

    @ApiOperation("获取用户信息")
    @GetMapping("/info")
    public Result<UserInfoDTO> getUserInfo() {
        Long userId = getCurrentUserId(request, jwtUtils);
        UserInfoDTO userInfo = userService.getUserInfo(userId);
        return Result.success(userInfo);
    }

    @ApiOperation("更新用户信息")
    @PutMapping("/update")
    public Result<Void> updateUserInfo(
            @RequestParam(required = false) String nickName,
            @RequestParam(required = false) String avatarUrl) {
        Long userId = getCurrentUserId(request, jwtUtils);
        userService.updateUserInfo(userId, nickName, avatarUrl);
        return Result.success();
    }

    @ApiOperation("退出登录")
    @PostMapping("/logout")
    public Result<Void> logout() {
        // 实际项目中可以处理token失效等逻辑
        return Result.success();
    }

}