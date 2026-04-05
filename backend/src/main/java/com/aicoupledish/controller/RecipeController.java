package com.aicoupledish.controller;

import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.RecipeDTO;
import com.aicoupledish.domain.req.CreateRecipeReq;
import com.aicoupledish.service.RecipeService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 菜谱控制器
 */
@Api(tags = "菜谱管理")
@RestController
@RequestMapping("/recipe")
@RequiredArgsConstructor
public class RecipeController {

    private final RecipeService recipeService;

    @ApiOperation("创建菜谱")
    @PostMapping("/create")
    public Result<Long> createRecipe(
            @RequestAttribute("userId") Long userId,
            @Validated @RequestBody CreateRecipeReq req) {
        Long recipeId = recipeService.createRecipe(userId, req);
        return Result.success(recipeId);
    }

    @ApiOperation("更新菜谱")
    @PutMapping("/update/{recipeId}")
    public Result<Void> updateRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId,
            @Validated @RequestBody CreateRecipeReq req) {
        recipeService.updateRecipe(userId, recipeId, req);
        return Result.success("更新成功");
    }

    @ApiOperation("删除菜谱")
    @DeleteMapping("/delete/{recipeId}")
    public Result<Void> deleteRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId) {
        recipeService.deleteRecipe(userId, recipeId);
        return Result.success("删除成功");
    }

    @ApiOperation("发布菜谱")
    @PostMapping("/publish/{recipeId}")
    public Result<Void> publishRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId) {
        recipeService.publishRecipe(userId, recipeId);
        return Result.success("发布成功");
    }

    @ApiOperation("获取菜谱详情")
    @GetMapping("/detail/{recipeId}")
    public Result<RecipeDTO> getRecipeDetail(
            @RequestAttribute(value = "userId", required = false) Long userId,
            @PathVariable Long recipeId) {
        RecipeDTO dto = recipeService.getRecipeDetail(userId, recipeId);
        return Result.success(dto);
    }

    @ApiOperation("获取我的菜谱列表")
    @GetMapping("/my")
    public Result<Page<RecipeDTO>> getMyRecipes(
            @RequestAttribute("userId") Long userId,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<RecipeDTO> page = recipeService.getMyRecipes(userId, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("获取情侣的菜谱列表")
    @GetMapping("/couple")
    public Result<Page<RecipeDTO>> getCoupleRecipes(
            @RequestAttribute("userId") Long userId,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<RecipeDTO> page = recipeService.getCoupleRecipes(userId, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("获取推荐菜谱")
    @GetMapping("/recommended")
    public Result<Page<RecipeDTO>> getRecommendedRecipes(
            @RequestAttribute("userId") Long userId,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<RecipeDTO> page = recipeService.getRecommendedRecipes(userId, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("点赞菜谱")
    @PostMapping("/like/{recipeId}")
    public Result<Void> likeRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId) {
        recipeService.likeRecipe(userId, recipeId);
        return Result.success("点赞成功");
    }

    @ApiOperation("取消点赞")
    @DeleteMapping("/like/{recipeId}")
    public Result<Void> unlikeRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId) {
        recipeService.unlikeRecipe(userId, recipeId);
        return Result.success("取消点赞成功");
    }

    @ApiOperation("收藏菜谱")
    @PostMapping("/collect/{recipeId}")
    public Result<Void> collectRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId) {
        recipeService.collectRecipe(userId, recipeId);
        return Result.success("收藏成功");
    }

    @ApiOperation("取消收藏")
    @DeleteMapping("/collect/{recipeId}")
    public Result<Void> uncollectRecipe(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long recipeId) {
        recipeService.uncollectRecipe(userId, recipeId);
        return Result.success("取消收藏成功");
    }

    @ApiOperation("获取收藏的菜谱")
    @GetMapping("/collected")
    public Result<Page<RecipeDTO>> getCollectedRecipes(
            @RequestAttribute("userId") Long userId,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<RecipeDTO> page = recipeService.getCollectedRecipes(userId, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("搜索菜谱")
    @GetMapping("/search")
    public Result<Page<RecipeDTO>> searchRecipes(
            @RequestAttribute("userId") Long userId,
            @RequestParam @ApiParam("关键词") String keyword,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<RecipeDTO> page = recipeService.searchRecipes(userId, keyword, pageNum, pageSize);
        return Result.success(page);
    }
}
