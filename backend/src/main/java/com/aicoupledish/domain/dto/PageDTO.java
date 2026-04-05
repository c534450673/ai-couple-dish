package com.aicoupledish.domain.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 分页响应DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PageDTO<T> {
    /**
     * 当前页码
     */
    private Long page;

    /**
     * 每页大小
     */
    private Long pageSize;

    /**
     * 总记录数
     */
    private Long total;

    /**
     * 总页数
     */
    private Long totalPages;

    /**
     * 数据列表
     */
    private List<T> list;

    /**
     * 是否还有下一页
     */
    private Boolean hasMore;

    /**
     * 构建分页响应
     */
    public static <T> PageDTO<T> of(List<T> list, Long page, Long pageSize, Long total) {
        Long totalPages = (total + pageSize - 1) / pageSize;
        Boolean hasMore = page < totalPages;
        return PageDTO.<T>builder()
                .page(page)
                .pageSize(pageSize)
                .total(total)
                .totalPages(totalPages)
                .list(list)
                .hasMore(hasMore)
                .build();
    }
}
