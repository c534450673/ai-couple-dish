package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.PosterDTO;
import com.aicoupledish.service.PosterService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 恋爱成就海报控制器
 */
@Api(tags = "恋爱成就海报工厂模块")
@RestController
@RequestMapping("/poster")
@RequiredArgsConstructor
public class PosterController extends BaseAuthController {

    private final PosterService posterService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取海报模板列表")
    @GetMapping("/templates")
    public Result<List<PosterDTO.TemplateDTO>> getTemplates(
            @ApiParam(value = "海报类型")
            @RequestParam(required = false) String posterType) {
        List<PosterDTO.TemplateDTO> templates = posterService.getTemplates(posterType);
        return Result.success(templates);
    }

    @ApiOperation("生成海报")
    @PostMapping("/generate")
    public Result<PosterDTO> generatePoster(@RequestBody PosterDTO.GenerateReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        PosterDTO dto = posterService.generatePoster(userId, req);
        return Result.success("海报生成成功", dto);
    }

    @ApiOperation("获取我的海报列表")
    @GetMapping("/list")
    public Result<List<PosterDTO>> getMyPosters(
            @ApiParam(value = "海报类型")
            @RequestParam(required = false) String posterType,
            @ApiParam(value = "数量限制，默认20")
            @RequestParam(required = false, defaultValue = "20") Integer limit) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<PosterDTO> posters = posterService.getMyPosters(userId, posterType, limit);
        return Result.success(posters);
    }

    @ApiOperation("获取海报详情")
    @GetMapping("/detail/{id}")
    public Result<PosterDTO> getPosterDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        PosterDTO dto = posterService.getPosterDetail(userId, id);
        return Result.success(dto);
    }

    @ApiOperation("删除海报")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deletePoster(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        posterService.deletePoster(userId, id);
        return Result.success();
    }

    @ApiOperation("获取海报分享数据")
    @GetMapping("/share/{id}")
    public Result<PosterDTO> getPosterShareData(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        PosterDTO dto = posterService.getPosterShareData(userId, id);
        return Result.success(dto);
    }
}
