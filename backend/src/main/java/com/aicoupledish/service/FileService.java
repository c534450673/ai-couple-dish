package com.aicoupledish.service;

import com.aicoupledish.domain.dto.FileUploadResult;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * 文件服务接口
 * 提供统一的文件操作能力，包括上传、删除、URL生成等
 */
public interface FileService {

    /**
     * 上传单张图片
     * @param userId 用户ID
     * @param file 图片文件
     * @return 上传结果
     */
    FileUploadResult uploadImage(Long userId, MultipartFile file);

    /**
     * 上传多张图片
     * @param userId 用户ID
     * @param files 图片文件数组
     * @return 上传结果列表
     */
    List<FileUploadResult> uploadImages(Long userId, MultipartFile[] files);

    /**
     * 删除文件
     * @param userId 用户ID（用于权限校验）
     * @param fileKey 文件key
     * @return 是否删除成功
     */
    boolean deleteFile(Long userId, String fileKey);

    /**
     * 获取文件访问URL
     * @param fileKey 文件key
     * @return 文件访问URL
     */
    String getFileUrl(String fileKey);

    /**
     * 检查用户是否有权删除指定文件
     * @param userId 用户ID
     * @param fileKey 文件key
     * @return 是否有权限
     */
    boolean canDelete(Long userId, String fileKey);
}
