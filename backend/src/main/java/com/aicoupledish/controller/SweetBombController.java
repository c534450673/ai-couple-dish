package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.SweetBombDTO;
import com.aicoupledish.service.SweetBombService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 随机甜蜜炸弹控制器
 */
@Api(tags = "随机甜蜜炸弹模块")
@RestController
@RequestMapping("/sweetBomb")
@RequiredArgsConstructor
public class SweetBombController extends BaseAuthController {

    private final SweetBombService sweetBombService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("生成甜蜜炸弹")
    @PostMapping("/generate")
    public Result<SweetBombDTO> generateBomb() {
        Long userId = getCurrentUserId(request, jwtUtils);
        SweetBombDTO dto = sweetBombService.generateBomb(userId);
        return Result.success("甜蜜炸弹已发送", dto);
    }

    @ApiOperation("获取未读炸弹列表")
    @GetMapping("/unread")
    public Result<List<SweetBombDTO>> getUnreadBombs() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<SweetBombDTO> bombs = sweetBombService.getUnreadBombs(userId);
        return Result.success(bombs);
    }

    @ApiOperation("获取炸弹详情")
    @GetMapping("/detail/{id}")
    public Result<SweetBombDTO> getBombDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        SweetBombDTO dto = sweetBombService.getBombDetail(userId, id);
        return Result.success(dto);
    }

    @ApiOperation("标记炸弹已读")
    @PostMapping("/read/{id}")
    public Result<Void> markAsRead(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        sweetBombService.markAsRead(userId, id);
        return Result.success();
    }

    @ApiOperation("回答炸弹问题")
    @PostMapping("/answer/{id}")
    public Result<Void> answerBomb(
            @PathVariable Long id,
            @ApiParam(value = "回答内容", required = true)
            @RequestParam String answerContent) {
        Long userId = getCurrentUserId(request, jwtUtils);
        sweetBombService.answerBomb(userId, id, answerContent);
        return Result.success("回答已发送");
    }

    @ApiOperation("获取炸弹历史")
    @GetMapping("/history")
    public Result<List<SweetBombDTO>> getBombHistory(
            @ApiParam(value = "数量限制，默认20")
            @RequestParam(required = false, defaultValue = "20") Integer limit) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<SweetBombDTO> bombs = sweetBombService.getBombHistory(userId, limit);
        return Result.success(bombs);
    }

    @ApiOperation("获取未读炸弹数量")
    @GetMapping("/unread/count")
    public Result<Integer> getUnreadCount() {
        Long userId = getCurrentUserId(request, jwtUtils);
        Integer count = sweetBombService.getUnreadCount(userId);
        return Result.success(count);
    }
}
