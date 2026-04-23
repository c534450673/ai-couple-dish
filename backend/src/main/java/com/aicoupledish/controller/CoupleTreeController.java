package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.CoupleTreeDTO;
import com.aicoupledish.domain.req.WaterTreeReq;
import com.aicoupledish.service.CoupleTreeService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 情侣爱心树控制器
 */
@Api(tags = "情侣爱心树模块")
@RestController
@RequestMapping("/coupleTree")
@RequiredArgsConstructor
public class CoupleTreeController extends BaseAuthController {

    private final CoupleTreeService coupleTreeService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取爱心树信息")
    @GetMapping("/info")
    public Result<CoupleTreeDTO> getTreeInfo() {
        Long userId = getCurrentUserId(request, jwtUtils);
        CoupleTreeDTO dto = coupleTreeService.getTreeInfo(userId);
        return Result.success(dto);
    }

    @ApiOperation("浇水（增加养分）")
    @PostMapping("/water")
    public Result<Void> waterTree(@Valid @RequestBody WaterTreeReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        coupleTreeService.waterTree(userId, req);
        return Result.success();
    }

    @ApiOperation("获取养分日志")
    @GetMapping("/nutrientLogs")
    public Result<List<CoupleTreeDTO.NutrientLogInfo>> getNutrientLogs(
            @ApiParam(value = "数量限制，默认20")
            @RequestParam(required = false, defaultValue = "20") Integer limit) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<CoupleTreeDTO.NutrientLogInfo> logs = coupleTreeService.getNutrientLogs(userId, limit);
        return Result.success(logs);
    }

    @ApiOperation("获取可用皮肤列表")
    @GetMapping("/skins")
    public Result<List<CoupleTreeDTO.SkinInfo>> getAvailableSkins() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<CoupleTreeDTO.SkinInfo> skins = coupleTreeService.getAvailableSkins(userId);
        return Result.success(skins);
    }

    @ApiOperation("切换皮肤")
    @PostMapping("/skin/change")
    public Result<Void> changeSkin(
            @ApiParam(value = "皮肤ID", required = true)
            @RequestParam String skinId) {
        Long userId = getCurrentUserId(request, jwtUtils);
        coupleTreeService.changeSkin(userId, skinId);
        return Result.success();
    }
}
