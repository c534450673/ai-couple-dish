package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.TimeCapsuleDTO;
import com.aicoupledish.domain.req.TimeCapsuleReq;
import com.aicoupledish.service.TimeCapsuleService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 时光胶囊控制器
 */
@Api(tags = "时光胶囊模块")
@RestController
@RequestMapping("/timeCapsule")
@RequiredArgsConstructor
public class TimeCapsuleController {

    private final TimeCapsuleService timeCapsuleService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("创建时光胶囊")
    @PostMapping("/create")
    public Result<Long> createTimeCapsule(@Valid @RequestBody TimeCapsuleReq req) {
        Long userId = getCurrentUserId();
        Long capsuleId = timeCapsuleService.createTimeCapsule(userId, req);
        return Result.success("时光胶囊创建成功", capsuleId);
    }

    @ApiOperation("获取时光胶囊列表")
    @GetMapping("/list")
    public Result<List<TimeCapsuleDTO>> getTimeCapsuleList() {
        Long userId = getCurrentUserId();
        List<TimeCapsuleDTO> list = timeCapsuleService.getTimeCapsuleList(userId);
        return Result.success(list);
    }

    @ApiOperation("获取时光胶囊详情")
    @GetMapping("/detail/{id}")
    public Result<TimeCapsuleDTO> getTimeCapsuleDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        TimeCapsuleDTO detail = timeCapsuleService.getTimeCapsuleDetail(userId, id);
        return Result.success(detail);
    }

    @ApiOperation("解锁时光胶囊")
    @PostMapping("/unlock/{id}")
    public Result<TimeCapsuleDTO> unlockTimeCapsule(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        TimeCapsuleDTO dto = timeCapsuleService.unlockTimeCapsule(userId, id);
        return Result.success("时光胶囊已解锁", dto);
    }

    @ApiOperation("删除时光胶囊")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteTimeCapsule(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        timeCapsuleService.deleteTimeCapsule(userId, id);
        return Result.success();
    }

    @ApiOperation("获取可解锁的时光胶囊")
    @GetMapping("/pending")
    public Result<List<TimeCapsuleDTO>> getPendingTimeCapsules() {
        Long userId = getCurrentUserId();
        List<TimeCapsuleDTO> list = timeCapsuleService.getPendingTimeCapsules(userId);
        return Result.success(list);
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
