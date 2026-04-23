package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 文件上传结果
 */
@Data
public class FileUploadResult {
    private String url;
    private String filename;
    private String originalFilename;
    private Long size;
    private String type;
    private String fileKey;

    public FileUploadResult() {}

    public FileUploadResult(String url, String filename, String originalFilename, Long size, String type, String fileKey) {
        this.url = url;
        this.filename = filename;
        this.originalFilename = originalFilename;
        this.size = size;
        this.type = type;
        this.fileKey = fileKey;
    }
}
