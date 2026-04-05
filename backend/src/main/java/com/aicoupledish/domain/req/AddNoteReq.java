package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import java.util.List;

/**
 * 添加笔记请求
 */
@Data
public class AddNoteReq {

    /**
     * 笔记标题
     */
    @NotBlank(message = "笔记标题不能为空")
    private String title;

    /**
     * 笔记内容
     */
    @NotBlank(message = "笔记内容不能为空")
    private String content;

    /**
     * 位置信息
     */
    private String location;

    /**
     * 纬度
     */
    private Double latitude;

    /**
     * 经度
     */
    private Double longitude;

    /**
     * 是否关联纪念日
     */
    private Integer isAnniversaryLinked;

    /**
     * 关联的纪念日ID
     */
    private Long anniversaryId;

    /**
     * 照片URLs
     */
    private List<String> photoUrls;
}