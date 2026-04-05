package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.CoupleRankDTO;
import com.aicoupledish.service.CoupleRankService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 情侣段位控制器
 */
@Api(tags = "情侣段位系统模块")
@RestController
@RequestMapping("/coupleRank")
@RequiredArgsConstructor
public class CoupleRankController {

    private final CoupleRankService coupleRankService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取段位信息")
    @GetMapping("/info")
    public Result<CoupleRankDTO> getRankInfo() {
        Long userId = getCurrentUserId();
        CoupleRankDTO dto = coupleRankService.getRankInfo(userId);
        return Result.success(dto);
    }

    @ApiOperation("获取段位排行榜")
    @GetMapping("/rankList")
    public Result<List<CoupleRankDTO>> getRankList(
            @ApiParam(value = "数量限制，默认100")
            @RequestParam(required = false, defaultValue = "100") Integer limit) {
        List<CoupleRankDTO> list = coupleRankService.getRankList(limit);
        return Result.success(list);
    }

    @ApiOperation("获取段位奖励列表")
    @GetMapping("/rewards")
    public Result<List<CoupleRankDTO.RankReward>> getRankRewards() {
        Long userId = getCurrentUserId();
        List<CoupleRankDTO.RankReward> rewards = coupleRankService.getRankRewards(userId);
        return Result.success(rewards);
    }

    @ApiOperation("领取段位奖励")
    @PostMapping("/claim/{rank}")
    public Result<Void> claimRankReward(@PathVariable String rank) {
        Long userId = getCurrentUserId();
        coupleRankService.claimRankReward(userId, rank);
        return Result.success("奖励领取成功");
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
