package com.aicoupledish.ai.tool;

import com.aicoupledish.ai.domain.AiPendingActionDTO;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.domain.dto.MenuDTO;
import com.aicoupledish.domain.dto.PageDTO;
import com.aicoupledish.domain.dto.RecipeDTO;
import com.aicoupledish.domain.req.AddMenuReq;
import com.aicoupledish.domain.req.CreateRecipeReq;
import com.aicoupledish.service.CoupleService;
import com.aicoupledish.service.MenuService;
import com.aicoupledish.service.RecipeService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class AiToolExecutor {

    private final MenuService menuService;
    private final CoupleService coupleService;
    private final RecipeService recipeService;
    private final ObjectMapper objectMapper;

    public ToolResult execute(Long userId, String toolName, String argumentsJson) {
        try {
            JsonNode args = argumentsJson == null || argumentsJson.isBlank()
                    ? objectMapper.createObjectNode()
                    : objectMapper.readTree(argumentsJson);

            if (AiToolDefinitions.WRITE_TOOLS.contains(toolName)) {
                return buildWritePreview(userId, toolName, args);
            }

            Object result = switch (toolName) {
                case "list_menus" -> listMenus(userId, args);
                case "search_menus" -> searchMenus(userId, args);
                case "get_menu_stats" -> menuService.getMenuStats(userId);
                case "get_couple_info" -> coupleService.getCoupleInfo(userId);
                case "get_couple_home" -> coupleService.getCoupleHome(userId);
                case "list_recipes" -> listRecipes(userId, args);
                case "search_recipes" -> searchRecipes(userId, args);
                case "recommend_dish" -> Map.of(
                        "hint", "请根据以下偏好给出3条具体推荐（餐厅名+菜品+理由）",
                        "preference", text(args, "preference"),
                        "occasion", text(args, "occasion")
                );
                default -> throw new BusinessException(9003, "未知工具: " + toolName);
            };
            return ToolResult.read(objectMapper.writeValueAsString(result));
        } catch (BusinessException e) {
            return ToolResult.error(e.getMessage());
        } catch (Exception e) {
            log.error("Tool execution failed: {}", toolName, e);
            return ToolResult.error("工具执行失败: " + e.getMessage());
        }
    }

    public Long confirmWrite(Long userId, AiPendingActionDTO pending) {
        return switch (pending.getActionType()) {
            case "add_menu" -> {
                AddMenuReq req = objectMapper.convertValue(pending.getPayload(), AddMenuReq.class);
                yield menuService.addMenu(userId, req);
            }
            case "create_recipe" -> {
                CreateRecipeReq req = objectMapper.convertValue(pending.getPayload(), CreateRecipeReq.class);
                yield recipeService.createRecipe(userId, req);
            }
            default -> throw new BusinessException(9003, "不支持的确认操作: " + pending.getActionType());
        };
    }

    private ToolResult buildWritePreview(Long userId, String toolName, JsonNode args) {
        Map<String, Object> payload = objectMapper.convertValue(args, new TypeReference<>() {});
        AiPendingActionDTO pending = new AiPendingActionDTO();
        pending.setActionId(UUID.randomUUID().toString());
        pending.setActionType(toolName);
        pending.setPayload(payload);

        if ("add_menu".equals(toolName)) {
            String restaurant = text(args, "restaurantName");
            if (restaurant == null || restaurant.isBlank()) {
                return ToolResult.error("餐厅名称不能为空");
            }
            pending.setTitle("添加菜单");
            pending.setSummary(String.format("餐厅：%s%s",
                    restaurant,
                    args.has("dishName") ? " · " + args.get("dishName").asText() : ""));
        } else if ("create_recipe".equals(toolName)) {
            String title = text(args, "title");
            if (title == null || title.isBlank()) {
                return ToolResult.error("菜谱标题不能为空");
            }
            pending.setTitle("创建菜谱");
            pending.setSummary("菜谱：" + title);
        }

        return ToolResult.pending(pending,
                "已生成操作预览，等待用户确认。actionId=" + pending.getActionId());
    }

    private PageDTO<MenuDTO> listMenus(Long userId, JsonNode args) {
        Integer status = intOrNull(args, "status");
        String keyword = text(args, "keyword");
        long page = longOrDefault(args, "page", 1L);
        long pageSize = longOrDefault(args, "pageSize", 10L);
        return menuService.getMenuList(userId, status, keyword, null, null, null, null,
                "time", "desc", page, pageSize);
    }

    private PageDTO<MenuDTO> searchMenus(Long userId, JsonNode args) {
        String keyword = text(args, "keyword");
        if (keyword == null || keyword.isBlank()) {
            throw new BusinessException(400, "搜索关键词不能为空");
        }
        return menuService.getMenuList(userId, null, keyword, null, null, null, null,
                "time", "desc", 1L, 10L);
    }

    private Map<String, Object> listRecipes(Long userId, JsonNode args) {
        int pageNum = (int) longOrDefault(args, "page", 1L);
        int pageSize = (int) longOrDefault(args, "pageSize", 10L);
        Page<RecipeDTO> page = recipeService.getCoupleRecipes(userId, pageNum, pageSize);
        Map<String, Object> m = new HashMap<>();
        m.put("total", page.getTotal());
        m.put("records", page.getRecords());
        return m;
    }

    private Map<String, Object> searchRecipes(Long userId, JsonNode args) {
        String keyword = text(args, "keyword");
        Page<RecipeDTO> page = recipeService.searchRecipes(userId, keyword, 1, 10);
        Map<String, Object> m = new HashMap<>();
        m.put("total", page.getTotal());
        m.put("records", page.getRecords());
        return m;
    }

    private static String text(JsonNode args, String field) {
        return args.has(field) && !args.get(field).isNull() ? args.get(field).asText() : null;
    }

    private static Integer intOrNull(JsonNode args, String field) {
        return args.has(field) && !args.get(field).isNull() ? args.get(field).asInt() : null;
    }

    private static long longOrDefault(JsonNode args, String field, long def) {
        return args.has(field) && !args.get(field).isNull() ? args.get(field).asLong() : def;
    }

    public record ToolResult(String content, AiPendingActionDTO pendingAction, boolean error) {
        static ToolResult read(String json) {
            return new ToolResult(json, null, false);
        }

        static ToolResult pending(AiPendingActionDTO pending, String msg) {
            return new ToolResult(msg, pending, false);
        }

        static ToolResult error(String msg) {
            return new ToolResult(msg, null, true);
        }
    }
}
