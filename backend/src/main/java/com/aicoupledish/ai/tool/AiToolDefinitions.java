package com.aicoupledish.ai.tool;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Agent 可用工具定义（OpenAI function calling 格式）
 */
public final class AiToolDefinitions {

    public static final Set<String> WRITE_TOOLS = Set.of("add_menu", "create_recipe");

    private AiToolDefinitions() {
    }

    public static List<Map<String, Object>> allTools() {
        List<Map<String, Object>> tools = new ArrayList<>();
        tools.add(fn("list_menus", "查询情侣私密菜单列表，可按状态或关键词筛选",
                props(
                        prop("status", "integer", "状态：0想去 1去过 2种草，可选"),
                        prop("keyword", "string", "搜索关键词，可选"),
                        prop("page", "integer", "页码，默认1"),
                        prop("pageSize", "integer", "每页数量，默认10")
                ), List.of()));
        tools.add(fn("search_menus", "按关键词搜索菜单中的餐厅或菜品", props(
                prop("keyword", "string", "搜索词")
        ), List.of("keyword")));
        tools.add(fn("get_menu_stats", "获取菜单统计数据", props(), List.of()));
        tools.add(fn("add_menu", "添加餐厅/菜品到私密菜单（需用户确认后才会写入）", props(
                prop("restaurantName", "string", "餐厅名称"),
                prop("dishName", "string", "菜品名称"),
                prop("dishCategory", "string", "分类标签"),
                prop("price", "number", "人均价格"),
                prop("location", "string", "位置"),
                prop("note", "string", "私密笔记"),
                prop("rating", "integer", "评分1-5"),
                prop("status", "integer", "0想去 1去过 2种草"),
                prop("eatenDate", "string", "用餐日期 yyyy-MM-dd")
        ), List.of("restaurantName")));
        tools.add(fn("get_couple_info", "获取当前用户的情侣关系信息", props(), List.of()));
        tools.add(fn("get_couple_home", "获取情侣主页概览（恋爱天数、统计等）", props(), List.of()));
        tools.add(fn("list_recipes", "获取情侣菜谱列表", props(
                prop("page", "integer", "页码"),
                prop("pageSize", "integer", "每页数量")
        ), List.of()));
        tools.add(fn("search_recipes", "搜索菜谱", props(
                prop("keyword", "string", "搜索关键词")
        ), List.of("keyword")));
        tools.add(fn("create_recipe", "创建菜谱（需用户确认后才会写入）", props(
                prop("title", "string", "菜谱标题"),
                prop("description", "string", "描述"),
                prop("difficulty", "string", "难度：简单/中等/困难"),
                prop("cookingTime", "integer", "烹饪时间分钟"),
                prop("servings", "integer", "份量"),
                prop("ingredients", "array", "食材列表 [{name, amount}]"),
                prop("steps", "array", "步骤列表 [{content}]"),
                prop("publish", "boolean", "是否发布")
        ), List.of("title")));
        tools.add(fn("recommend_dish", "根据用户偏好推荐菜品或餐厅（不写入数据库）", props(
                prop("preference", "string", "口味偏好或场景描述"),
                prop("occasion", "string", "场合：约会/日常/纪念日等")
        ), List.of("preference")));
        return tools;
    }

    private static Map<String, Object> fn(String name, String description,
                                          Map<String, Object> properties,
                                          List<String> required) {
        Map<String, Object> params = new HashMap<>();
        params.put("type", "object");
        params.put("properties", properties);
        if (!required.isEmpty()) {
            params.put("required", required);
        }
        Map<String, Object> function = new HashMap<>();
        function.put("name", name);
        function.put("description", description);
        function.put("parameters", params);
        Map<String, Object> tool = new HashMap<>();
        tool.put("type", "function");
        tool.put("function", function);
        return tool;
    }

    private static Map<String, Object> props(Map<String, Object>... entries) {
        Map<String, Object> p = new HashMap<>();
        for (Map<String, Object> e : entries) {
            p.putAll(e);
        }
        return p;
    }

    private static Map<String, Object> prop(String name, String type, String description) {
        Map<String, Object> m = new HashMap<>();
        m.put("type", type);
        m.put("description", description);
        return Map.of(name, m);
    }
}
