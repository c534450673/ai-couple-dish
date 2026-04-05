package com.aicoupledish.service.impl;

import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.RecipeCollectMapper;
import com.aicoupledish.dao.mapper.RecipeLikeMapper;
import com.aicoupledish.dao.mapper.RecipeMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.Recipe;
import com.aicoupledish.dao.model.RecipeCollect;
import com.aicoupledish.dao.model.RecipeLike;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.RecipeDTO;
import com.aicoupledish.domain.req.CreateRecipeReq;
import com.aicoupledish.service.RecipeService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

/**
 * 菜谱服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RecipeServiceImpl implements RecipeService {

    private final RecipeMapper recipeMapper;
    private final RecipeLikeMapper recipeLikeMapper;
    private final RecipeCollectMapper recipeCollectMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;

    /**
     * 状态：草稿
     */
    private static final int STATUS_DRAFT = 0;
    /**
     * 状态：已发布
     */
    private static final int STATUS_PUBLISHED = 1;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createRecipe(Long userId, CreateRecipeReq req) {
        Recipe recipe = new Recipe();
        recipe.setUserId(userId);
        recipe.setTitle(req.getTitle());
        recipe.setCoverUrl(req.getCoverUrl());
        recipe.setDescription(req.getDescription());
        recipe.setDifficulty(req.getDifficulty());
        recipe.setCookingTime(req.getCookingTime());
        recipe.setServings(req.getServings());
        recipe.setStatus(req.getPublish() != null && req.getPublish() ? STATUS_PUBLISHED : STATUS_DRAFT);
        recipe.setLikeCount(0);
        recipe.setCollectCount(0);
        recipe.setIsDeleted(0);

        // 转换食材和步骤为JSON
        if (req.getIngredients() != null) {
            recipe.setIngredients(JSONUtil.toJsonStr(req.getIngredients()));
        }
        if (req.getSteps() != null) {
            List<RecipeDTO.StepDTO> steps = new ArrayList<>();
            for (int i = 0; i < req.getSteps().size(); i++) {
                RecipeDTO.StepDTO step = new RecipeDTO.StepDTO();
                step.setStepNo(i + 1);
                step.setContent(req.getSteps().get(i).getContent());
                step.setImageUrl(req.getSteps().get(i).getImageUrl());
                steps.add(step);
            }
            recipe.setSteps(JSONUtil.toJsonStr(steps));
        }

        recipeMapper.insert(recipe);
        log.info("用户 {} 创建菜谱成功, recipeId={}", userId, recipe.getId());
        return recipe.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateRecipe(Long userId, Long recipeId, CreateRecipeReq req) {
        Recipe recipe = getRecipeById(recipeId);
        validateRecipeOwner(recipe, userId);

        recipe.setTitle(req.getTitle());
        recipe.setCoverUrl(req.getCoverUrl());
        recipe.setDescription(req.getDescription());
        recipe.setDifficulty(req.getDifficulty());
        recipe.setCookingTime(req.getCookingTime());
        recipe.setServings(req.getServings());

        if (req.getIngredients() != null) {
            recipe.setIngredients(JSONUtil.toJsonStr(req.getIngredients()));
        }
        if (req.getSteps() != null) {
            List<RecipeDTO.StepDTO> steps = new ArrayList<>();
            for (int i = 0; i < req.getSteps().size(); i++) {
                RecipeDTO.StepDTO step = new RecipeDTO.StepDTO();
                step.setStepNo(i + 1);
                step.setContent(req.getSteps().get(i).getContent());
                step.setImageUrl(req.getSteps().get(i).getImageUrl());
                steps.add(step);
            }
            recipe.setSteps(JSONUtil.toJsonStr(steps));
        }

        recipeMapper.updateById(recipe);
        log.info("用户 {} 更新菜谱 {}", userId, recipeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteRecipe(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);
        validateRecipeOwner(recipe, userId);

        recipeMapper.deleteById(recipeId);
        log.info("用户 {} 删除菜谱 {}", userId, recipeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void publishRecipe(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);
        validateRecipeOwner(recipe, userId);

        if (recipe.getStatus() == STATUS_PUBLISHED) {
            throw new BusinessException("菜谱已发布");
        }

        recipe.setStatus(STATUS_PUBLISHED);
        recipeMapper.updateById(recipe);
        log.info("用户 {} 发布菜谱 {}", userId, recipeId);
    }

    @Override
    public RecipeDTO getRecipeDetail(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);

        // 如果是草稿，只有创建者可以查看
        if (recipe.getStatus() == STATUS_DRAFT) {
            if (userId == null || !recipe.getUserId().equals(userId)) {
                throw new BusinessException("菜谱不存在");
            }
        }

        RecipeDTO dto = convertToRecipeDTO(recipe);

        // 检查是否点赞/收藏
        if (userId != null) {
            // 检查是否已点赞
            RecipeLike like = recipeLikeMapper.selectOne(
                    new LambdaQueryWrapper<RecipeLike>()
                            .eq(RecipeLike::getRecipeId, recipeId)
                            .eq(RecipeLike::getUserId, userId)
            );
            dto.setLiked(like != null);

            // 检查是否已收藏
            RecipeCollect collect = recipeCollectMapper.selectOne(
                    new LambdaQueryWrapper<RecipeCollect>()
                            .eq(RecipeCollect::getRecipeId, recipeId)
                            .eq(RecipeCollect::getUserId, userId)
            );
            dto.setCollected(collect != null);
        }

        return dto;
    }

    @Override
    public Page<RecipeDTO> getMyRecipes(Long userId, Integer pageNum, Integer pageSize) {
        Page<Recipe> page = new Page<>(pageNum, pageSize);
        Page<Recipe> result = recipeMapper.selectPage(page,
                new LambdaQueryWrapper<Recipe>()
                        .eq(Recipe::getUserId, userId)
                        .eq(Recipe::getIsDeleted, 0)
                        .orderByDesc(Recipe::getCreateTime));

        return convertToRecipeDTOPage(result);
    }

    @Override
    public Page<RecipeDTO> getCoupleRecipes(Long userId, Integer pageNum, Integer pageSize) {
        // 获取情侣ID
        List<Long> userIds = getCoupleUserIds(userId);
        userIds.add(userId);

        Page<Recipe> page = new Page<>(pageNum, pageSize);
        Page<Recipe> result = recipeMapper.selectPage(page,
                new LambdaQueryWrapper<Recipe>()
                        .in(Recipe::getUserId, userIds)
                        .eq(Recipe::getStatus, STATUS_PUBLISHED)
                        .eq(Recipe::getIsDeleted, 0)
                        .orderByDesc(Recipe::getCreateTime));

        return convertToRecipeDTOPage(result);
    }

    @Override
    public Page<RecipeDTO> getRecommendedRecipes(Long userId, Integer pageNum, Integer pageSize) {
        // 简单实现：按点赞数排序
        Page<Recipe> page = new Page<>(pageNum, pageSize);
        Page<Recipe> result = recipeMapper.selectPage(page,
                new LambdaQueryWrapper<Recipe>()
                        .eq(Recipe::getStatus, STATUS_PUBLISHED)
                        .eq(Recipe::getIsDeleted, 0)
                        .orderByDesc(Recipe::getLikeCount)
                        .orderByDesc(Recipe::getCreateTime));

        return convertToRecipeDTOPage(result);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void likeRecipe(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);
        if (recipe.getStatus() != STATUS_PUBLISHED) {
            throw new BusinessException("菜谱未发布");
        }

        // 检查是否已点赞（去重）
        RecipeLike existingLike = recipeLikeMapper.selectOne(
                new LambdaQueryWrapper<RecipeLike>()
                        .eq(RecipeLike::getRecipeId, recipeId)
                        .eq(RecipeLike::getUserId, userId)
        );

        if (existingLike != null) {
            throw new BusinessException("您已点赞过该菜谱");
        }

        // 记录点赞关系
        RecipeLike like = new RecipeLike();
        like.setRecipeId(recipeId);
        like.setUserId(userId);
        recipeLikeMapper.insert(like);

        // 使用原子更新增加点赞数
        recipeMapper.incrementLikeCount(recipeId);
        log.info("用户 {} 点赞菜谱 {}", userId, recipeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void unlikeRecipe(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);

        // 检查是否已点赞
        RecipeLike existingLike = recipeLikeMapper.selectOne(
                new LambdaQueryWrapper<RecipeLike>()
                        .eq(RecipeLike::getRecipeId, recipeId)
                        .eq(RecipeLike::getUserId, userId)
        );

        if (existingLike == null) {
            throw new BusinessException("您未点赞过该菜谱");
        }

        // 删除点赞关系
        recipeLikeMapper.deleteById(existingLike.getId());

        // 使用原子更新减少点赞数
        recipeMapper.decrementLikeCount(recipeId);
        log.info("用户 {} 取消点赞菜谱 {}", userId, recipeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void collectRecipe(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);
        if (recipe.getStatus() != STATUS_PUBLISHED) {
            throw new BusinessException("菜谱未发布");
        }

        // 检查是否已收藏（去重）
        RecipeCollect existingCollect = recipeCollectMapper.selectOne(
                new LambdaQueryWrapper<RecipeCollect>()
                        .eq(RecipeCollect::getRecipeId, recipeId)
                        .eq(RecipeCollect::getUserId, userId)
        );

        if (existingCollect != null) {
            throw new BusinessException("您已收藏过该菜谱");
        }

        // 记录收藏关系
        RecipeCollect collect = new RecipeCollect();
        collect.setRecipeId(recipeId);
        collect.setUserId(userId);
        recipeCollectMapper.insert(collect);

        // 使用原子更新增加收藏数
        recipeMapper.incrementCollectCount(recipeId);
        log.info("用户 {} 收藏菜谱 {}", userId, recipeId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void uncollectRecipe(Long userId, Long recipeId) {
        Recipe recipe = getRecipeById(recipeId);

        // 检查是否已收藏
        RecipeCollect existingCollect = recipeCollectMapper.selectOne(
                new LambdaQueryWrapper<RecipeCollect>()
                        .eq(RecipeCollect::getRecipeId, recipeId)
                        .eq(RecipeCollect::getUserId, userId)
        );

        if (existingCollect == null) {
            throw new BusinessException("您未收藏过该菜谱");
        }

        // 删除收藏关系
        recipeCollectMapper.deleteById(existingCollect.getId());

        // 使用原子更新减少收藏数
        recipeMapper.decrementCollectCount(recipeId);
        log.info("用户 {} 取消收藏菜谱 {}", userId, recipeId);
    }

    @Override
    public Page<RecipeDTO> getCollectedRecipes(Long userId, Integer pageNum, Integer pageSize) {
        // 获取用户收藏的菜谱ID列表
        List<RecipeCollect> collects = recipeCollectMapper.selectList(
                new LambdaQueryWrapper<RecipeCollect>()
                        .eq(RecipeCollect::getUserId, userId)
                        .orderByDesc(RecipeCollect::getCreateTime)
        );

        if (collects.isEmpty()) {
            Page<RecipeDTO> emptyPage = new Page<>(pageNum, pageSize);
            emptyPage.setRecords(new ArrayList<>());
            emptyPage.setTotal(0);
            return emptyPage;
        }

        // 获取收藏的菜谱ID
        List<Long> recipeIds = collects.stream()
                .map(RecipeCollect::getRecipeId)
                .collect(Collectors.toList());

        // 查询菜谱信息
        List<Recipe> recipes = recipeMapper.selectBatchIds(recipeIds);
        Map<Long, Recipe> recipeMap = recipes.stream()
                .collect(Collectors.toMap(Recipe::getId, r -> r, (a, b) -> a));

        // 批量获取用户信息
        Set<Long> userIds = recipes.stream()
                .map(Recipe::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = getUserMap(userIds);

        // 按收藏时间倒序构建结果
        List<RecipeDTO> records = collects.stream()
                .map(collect -> {
                    Recipe recipe = recipeMap.get(collect.getRecipeId());
                    if (recipe == null || recipe.getIsDeleted() == 1) {
                        return null; // 过滤已删除的菜谱
                    }
                    RecipeDTO dto = new RecipeDTO();
                    BeanUtils.copyProperties(recipe, dto);

                    if (recipe.getIngredients() != null) {
                        dto.setIngredients(JSONUtil.toList(recipe.getIngredients(), RecipeDTO.IngredientDTO.class));
                    }
                    if (recipe.getSteps() != null) {
                        dto.setSteps(JSONUtil.toList(recipe.getSteps(), RecipeDTO.StepDTO.class));
                    }

                    dto.setDifficultyDesc(getDifficultyDesc(recipe.getDifficulty()));
                    dto.setCollected(true);
                    dto.setCollectTime(collect.getCreateTime() != null ? collect.getCreateTime().toString() : null);

                    User user = userMap.get(recipe.getUserId());
                    if (user != null) {
                        dto.setUserName(user.getNickName());
                        dto.setUserAvatar(user.getAvatarUrl());
                    }

                    return dto;
                })
                .filter(Objects::nonNull)
                .collect(Collectors.toList());

        // 分页处理
        int total = records.size();
        // 参数校验，确保pageNum和pageSize有效
        int validPageNum = Math.max(1, pageNum);
        int validPageSize = Math.max(1, pageSize);
        int fromIndex = (validPageNum - 1) * validPageSize;
        int toIndex = Math.min(fromIndex + validPageSize, total);

        Page<RecipeDTO> resultPage = new Page<>(validPageNum, validPageSize);
        resultPage.setRecords(fromIndex < total ? records.subList(fromIndex, toIndex) : new ArrayList<>());
        resultPage.setTotal(total);

        return resultPage;
    }

    @Override
    public Page<RecipeDTO> searchRecipes(Long userId, String keyword, Integer pageNum, Integer pageSize) {
        Page<Recipe> page = new Page<>(pageNum, pageSize);

        LambdaQueryWrapper<Recipe> wrapper = new LambdaQueryWrapper<Recipe>()
                .eq(Recipe::getStatus, STATUS_PUBLISHED)
                .eq(Recipe::getIsDeleted, 0);

        // 只有关键词不为空时才添加搜索条件
        if (keyword != null && !keyword.trim().isEmpty()) {
            wrapper.and(w -> w
                    .like(Recipe::getTitle, keyword)
                    .or()
                    .like(Recipe::getDescription, keyword)
            );
        }

        wrapper.orderByDesc(Recipe::getCreateTime);

        Page<Recipe> result = recipeMapper.selectPage(page, wrapper);
        return convertToRecipeDTOPage(result);
    }

    /**
     * 根据ID获取菜谱
     */
    private Recipe getRecipeById(Long recipeId) {
        Recipe recipe = recipeMapper.selectById(recipeId);
        if (recipe == null || recipe.getIsDeleted() == 1) {
            throw new BusinessException("菜谱不存在");
        }
        return recipe;
    }

    /**
     * 验证菜谱所有者
     */
    private void validateRecipeOwner(Recipe recipe, Long userId) {
        if (!recipe.getUserId().equals(userId)) {
            throw new BusinessException("无权操作该菜谱");
        }
    }

    /**
     * 获取情侣的用户ID列表
     */
    private List<Long> getCoupleUserIds(Long userId) {
        List<Couple> couples = coupleMapper.selectList(
                new LambdaQueryWrapper<Couple>()
                        .eq(Couple::getStatus, 1)
                        .and(wrapper -> wrapper
                                .eq(Couple::getUser1Id, userId)
                                .or()
                                .eq(Couple::getUser2Id, userId))
        );

        List<Long> userIds = new ArrayList<>();
        for (Couple couple : couples) {
            if (!couple.getUser1Id().equals(userId)) {
                userIds.add(couple.getUser1Id());
            }
            if (!couple.getUser2Id().equals(userId)) {
                userIds.add(couple.getUser2Id());
            }
        }
        return userIds;
    }

    /**
     * 转换为DTO
     */
    private RecipeDTO convertToRecipeDTO(Recipe recipe) {
        RecipeDTO dto = new RecipeDTO();
        BeanUtils.copyProperties(recipe, dto);

        // 解析食材
        if (recipe.getIngredients() != null) {
            dto.setIngredients(JSONUtil.toList(recipe.getIngredients(), RecipeDTO.IngredientDTO.class));
        }

        // 解析步骤
        if (recipe.getSteps() != null) {
            dto.setSteps(JSONUtil.toList(recipe.getSteps(), RecipeDTO.StepDTO.class));
        }

        // 难度描述
        dto.setDifficultyDesc(getDifficultyDesc(recipe.getDifficulty()));

        // 获取用户信息
        User user = userMapper.selectById(recipe.getUserId());
        if (user != null) {
            dto.setUserName(user.getNickName());
            dto.setUserAvatar(user.getAvatarUrl());
        }

        return dto;
    }

    /**
     * 转换分页
     */
    private Page<RecipeDTO> convertToRecipeDTOPage(Page<Recipe> page) {
        Page<RecipeDTO> dtoPage = new Page<>();
        BeanUtils.copyProperties(page, dtoPage, "records");

        // 批量获取用户信息
        Set<Long> userIds = page.getRecords().stream()
                .map(Recipe::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = getUserMap(userIds);

        List<RecipeDTO> records = page.getRecords().stream()
                .map(recipe -> {
                    RecipeDTO dto = new RecipeDTO();
                    BeanUtils.copyProperties(recipe, dto);

                    if (recipe.getIngredients() != null) {
                        dto.setIngredients(JSONUtil.toList(recipe.getIngredients(), RecipeDTO.IngredientDTO.class));
                    }
                    if (recipe.getSteps() != null) {
                        dto.setSteps(JSONUtil.toList(recipe.getSteps(), RecipeDTO.StepDTO.class));
                    }

                    dto.setDifficultyDesc(getDifficultyDesc(recipe.getDifficulty()));

                    User user = userMap.get(recipe.getUserId());
                    if (user != null) {
                        dto.setUserName(user.getNickName());
                        dto.setUserAvatar(user.getAvatarUrl());
                    }

                    return dto;
                })
                .collect(Collectors.toList());

        dtoPage.setRecords(records);
        return dtoPage;
    }

    /**
     * 获取难度描述
     */
    private String getDifficultyDesc(String difficulty) {
        if (difficulty == null) {
            return null;
        }
        switch (difficulty) {
            case "easy":
                return "简单";
            case "medium":
                return "中等";
            case "hard":
                return "困难";
            default:
                return difficulty;
        }
    }

    /**
     * 批量获取用户信息
     */
    private Map<Long, User> getUserMap(Set<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return Collections.emptyMap();
        }
        List<User> users = userMapper.selectBatchIds(userIds);
        return users.stream().collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));
    }
}
