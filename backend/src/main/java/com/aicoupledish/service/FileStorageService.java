package com.aicoupledish.service;

import com.aicoupledish.domain.dto.FileUploadResult;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * 文件存储服务接口
 * 抽象文件存储操作，支持本地存储、云存储等多种实现
 */
public interface FileStorageService {

    /**
     * 上传单张图片
     * @param file 图片文件
     * @return 上传结果
     */
    FileUploadResult uploadImage(MultipartFile file);

    /**
     * 上传多张图片
     * @param files 图片文件数组
     * @return 上传结果列表
     */
    List<FileUploadResult> uploadImages(MultipartFile[] files);

    /**
     * 删除文件
     * @param fileKey 文件key（相对路径）
     * @return 是否删除成功
     */
    boolean deleteFile(String fileKey);

    /**
     * 获取文件访问URL
     * @param fileKey 文件key
     * @return 文件访问URL
     */
    String getFileUrl(String fileKey);

    /**
     * 检查是否是图片文件
     * @param file 文件
     * @return 是否为图片
     */
    boolean isImage(MultipartFile file);

    /**
     * 获取允许的图片扩展名
     */
    default String[] getAllowedImageExtensions() {
        return new String[]{"jpg", "jpeg", "png", "gif", "webp"};
    }

    /**
     * 获取允许的MIME类型
     */
    default String[] getAllowedMimeTypes() {
        return new String[]{"image/jpeg", "image/png", "image/gif", "image/webp"};
    }

    /**
     * 获取最大文件大小（字节）
     */
    default long getMaxFileSize() {
        return 10 * 1024 * 1024; // 10MB
    }
}
