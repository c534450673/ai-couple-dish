package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.HeartMomentDTO;
import com.aicoupledish.domain.req.HeartMomentReq;
import com.aicoupledish.service.HeartMomentService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 心动时刻控制器
 */
@Api(tags = "心动时刻模块")
@RestController
@RequestMapping("/heartMoment")
@RequiredArgsConstructor
public class HeartMomentController {

    private final HeartMomentService heartMomentService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("创建心动时刻")
    @PostMapping("/create")
    public Result<Long> createHeartMoment(@Valid @RequestBody HeartMomentReq req) {
        Long userId = getCurrentUserId();
        Long momentId = heartMomentService.createHeartMoment(userId, req);
        return Result.success("心动时刻创建成功", momentId);
    }

    @ApiOperation("获取心动时刻列表")
    @GetMapping("/list")
    public Result<List<HeartMomentDTO>> getHeartMomentList(
            @RequestParam(required = false) Long page,
            @RequestParam(required = false) Long pageSize) {
        Long userId = getCurrentUserId();
        List<HeartMomentDTO> list = heartMomentService.getHeartMomentList(userId, page, pageSize);
        return Result.success(list);
    }

    @ApiOperation("删除心动时刻")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteHeartMoment(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        heartMomentService.deleteHeartMoment(userId, id);
        return Result.success();
    }

    @ApiOperation("获取随机心动时刻")
    @GetMapping("/random")
    public Result<HeartMomentDTO> getRandomHeartMoment() {
        Long userId = getCurrentUserId();
        HeartMomentDTO dto = heartMomentService.getRandomHeartMoment(userId);
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
