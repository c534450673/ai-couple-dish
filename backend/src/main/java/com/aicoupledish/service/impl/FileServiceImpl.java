package com.aicoupledish.service.impl;

import cn.hutool.core.util.StrUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.domain.dto.FileUploadResult;
import com.aicoupledish.service.FileService;
import com.aicoupledish.service.FileStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * 文件服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class FileServiceImpl implements FileService {

    private final FileStorageService fileStorageService;

    @Override
    public FileUploadResult uploadImage(Long userId, MultipartFile file) {
        log.info("用户上传图片: userId={}, filename={}", userId, file.getOriginalFilename());
        return fileStorageService.uploadImage(file);
    }

    @Override
    public List<FileUploadResult> uploadImages(Long userId, MultipartFile[] files) {
        log.info("用户上传多张图片: userId={}, count={}", userId, files.length);
        return fileStorageService.uploadImages(files);
    }

    @Override
    public boolean deleteFile(Long userId, String fileKey) {
        if (!canDelete(userId, fileKey)) {
            log.warn("用户无权删除文件: userId={}, fileKey={}", userId, fileKey);
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        log.info("删除文件: userId={}, fileKey={}", userId, fileKey);
        return fileStorageService.deleteFile(fileKey);
    }

    @Override
    public String getFileUrl(String fileKey) {
        return fileStorageService.getFileUrl(fileKey);
    }

    @Override
    public boolean canDelete(Long userId, String fileKey) {
        if (userId == null || !StrUtil.isNotBlank(fileKey)) {
            return false;
        }
        // 安全策略：用户只能删除自己上传的文件
        // 文件key格式包含用户ID前缀，例如：user/{userId}/yyyy/MM/dd/uuid.jpg
        String expectedPrefix = "user/" + userId + "/";
        return fileKey.startsWith(expectedPrefix);
    }
}
