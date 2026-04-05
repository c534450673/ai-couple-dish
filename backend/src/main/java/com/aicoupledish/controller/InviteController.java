package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.InviteCodeDTO;
import com.aicoupledish.domain.dto.InviteStatsDTO;
import com.aicoupledish.domain.dto.ReferralDTO;
import com.aicoupledish.service.InviteService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 邀请返利控制器
 */
@Api(tags = "分层邀请返利体系模块")
@RestController
@RequestMapping("/invite")
@RequiredArgsConstructor
public class InviteController {

    private final InviteService inviteService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取我的邀请码")
    @GetMapping("/code")
    public Result<InviteCodeDTO> getMyInviteCode() {
        Long userId = getCurrentUserId();
        InviteCodeDTO dto = inviteService.getOrCreateInviteCode(userId);
        return Result.success(dto);
    }

    @ApiOperation("使用邀请码")
    @PostMapping("/use")
    public Result<Void> useInviteCode(
            @ApiParam(value = "邀请码", required = true)
            @RequestParam String inviteCode) {
        Long userId = getCurrentUserId();
        inviteService.useInviteCode(userId, inviteCode);
        return Result.success("邀请码使用成功");
    }

    @ApiOperation("获取邀请记录列表")
    @GetMapping("/referrals")
    public Result<List<ReferralDTO>> getReferralList(
            @ApiParam(value = "数量限制，默认50")
            @RequestParam(required = false, defaultValue = "50") Integer limit) {
        Long userId = getCurrentUserId();
        List<ReferralDTO> list = inviteService.getReferralList(userId, limit);
        return Result.success(list);
    }

    @ApiOperation("获取邀请统计")
    @GetMapping("/stats")
    public Result<InviteStatsDTO> getInviteStats() {
        Long userId = getCurrentUserId();
        InviteStatsDTO stats = inviteService.getInviteStats(userId);
        return Result.success(stats);
    }

    @ApiOperation("获取邀请排行榜")
    @GetMapping("/rank")
    public Result<List<InviteStatsDTO.InviteRankItem>> getInviteRankList(
            @ApiParam(value = "数量限制，默认10")
            @RequestParam(required = false, defaultValue = "10") Integer limit) {
        List<InviteStatsDTO.InviteRankItem> rankList = inviteService.getInviteRankList(limit);
        return Result.success(rankList);
    }

    @ApiOperation("验证邀请码（公开接口）")
    @GetMapping("/validate")
    public Result<Boolean> validateInviteCode(
            @ApiParam(value = "邀请码", required = true)
            @RequestParam String inviteCode) {
        boolean valid = inviteService.validateInviteCode(inviteCode);
        return Result.success(valid);
    }

    @ApiOperation("获取邀请码信息（公开接口）")
    @GetMapping("/info/{inviteCode}")
    public Result<InviteCodeDTO> getInviteCodeInfo(@PathVariable String inviteCode) {
        InviteCodeDTO dto = inviteService.getInviteCodeInfo(inviteCode);
        if (dto == null) {
            return Result.error(404, "邀请码不存在");
        }
        return Result.success(dto);
    }

    private Long getCurrentUserId() {
        String token = request.getHeader("Authorization");
        if (token == null || token.isEmpty()) {
            throw new BusinessException(9001, "请先登录");
        }
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            throw new BusinessException(9001, "无效的登录凭证");
        }
        return userId;
    }
}
