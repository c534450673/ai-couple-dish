package com.aicoupledish.service.impl;

import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.StrUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.domain.dto.FileUploadResult;
import com.aicoupledish.service.FileStorageService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 本地文件存储服务实现
 */
@Slf4j
@Service
public class LocalFileStorageServiceImpl implements FileStorageService {

    @Value("${file.upload.path:/app/uploads}")
    private String uploadPath;

    @Value("${file.upload.base-url:http://localhost:8080/api/uploads}")
    private String baseUrl;

    // 图片文件头魔数映射
    private static final Map<String, byte[]> IMAGE_MAGIC_NUMBERS = new HashMap<>();
    static {
        IMAGE_MAGIC_NUMBERS.put("jpg", new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF});
        IMAGE_MAGIC_NUMBERS.put("jpeg", new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF});
        IMAGE_MAGIC_NUMBERS.put("png", new byte[]{(byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A});
        IMAGE_MAGIC_NUMBERS.put("gif", new byte[]{'G', 'I', 'F'});
        IMAGE_MAGIC_NUMBERS.put("webp", new byte[]{'R', 'I', 'F', 'F'});
    }

    @Override
    public FileUploadResult uploadImage(MultipartFile file) {
        validateFile(file);

        String extension = FileUtil.extName(file.getOriginalFilename()).toLowerCase();
        String newFilename = IdUtil.simpleUUID() + "." + extension;
        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        String dirPath = uploadPath + File.separator + datePath;

        createDirectory(dirPath);

        File destFile = new File(dirPath + File.separator + newFilename);
        try {
            file.transferTo(destFile);
        } catch (IOException e) {
            log.error("文件保存失败: {}", e.getMessage(), e);
            throw new BusinessException(9002, "文件上传失败: " + e.getMessage());
        }

        String fileKey = datePath + "/" + newFilename;
        String fileUrl = baseUrl + "/" + fileKey;

        log.info("文件上传成功: fileKey={}, size={}", fileKey, file.getSize());

        return new FileUploadResult(
            fileUrl,
            newFilename,
            file.getOriginalFilename(),
            file.getSize(),
            extension,
            fileKey
        );
    }

    @Override
    public List<FileUploadResult> uploadImages(MultipartFile[] files) {
        if (files == null || files.length == 0) {
            throw BusinessException.PARAM_INVALID;
        }

        if (files.length > 9) {
            throw BusinessException.PARAM_INVALID;
        }

        List<FileUploadResult> results = new ArrayList<>();
        for (MultipartFile file : files) {
            try {
                results.add(uploadImage(file));
            } catch (BusinessException e) {
                log.warn("单文件上传失败: {}", e.getMessage());
            }
        }
        return results;
    }

    @Override
    public boolean deleteFile(String fileKey) {
        if (StrUtil.isBlank(fileKey)) {
            return false;
        }

        String fullPath = uploadPath + File.separator + fileKey.replace("/", File.separator);
        File file = new File(fullPath);

        if (file.exists()) {
            boolean deleted = file.delete();
            if (deleted) {
                log.info("文件删除成功: fileKey={}", fileKey);
            }
            return deleted;
        }

        log.warn("文件不存在: fileKey={}", fileKey);
        return false;
    }

    @Override
    public String getFileUrl(String fileKey) {
        if (StrUtil.isBlank(fileKey)) {
            return null;
        }
        return baseUrl + "/" + fileKey;
    }

    @Override
    public boolean isImage(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            return false;
        }

        String extension = FileUtil.extName(file.getOriginalFilename()).toLowerCase();
        return isAllowedImageType(extension) && isAllowedMimeType(file.getContentType());
    }

    /**
     * 验证文件
     */
    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw BusinessException.PARAM_INVALID;
        }

        String originalFilename = file.getOriginalFilename();
        if (StrUtil.isBlank(originalFilename)) {
            throw BusinessException.PARAM_INVALID;
        }

        // 验证文件大小
        if (file.getSize() > getMaxFileSize()) {
            throw BusinessException.PARAM_INVALID;
        }

        String extension = FileUtil.extName(originalFilename).toLowerCase();

        // 验证文件扩展名
        if (!isAllowedImageType(extension)) {
            throw BusinessException.PARAM_INVALID;
        }

        // 验证MIME类型
        if (!isAllowedMimeType(file.getContentType())) {
            log.warn("非法MIME类型: {}, 文件名: {}", file.getContentType(), originalFilename);
            throw BusinessException.PARAM_INVALID;
        }

        // 验证文件头（魔数校验）
        validateFileHeader(file, extension);
    }

    /**
     * 验证文件头魔数
     */
    private void validateFileHeader(MultipartFile file, String extension) {
        byte[] expectedMagic = IMAGE_MAGIC_NUMBERS.get(extension);
        if (expectedMagic == null) {
            return;
        }

        try (InputStream is = file.getInputStream()) {
            byte[] header = new byte[expectedMagic.length];
            int read = is.read(header);
            if (read < expectedMagic.length) {
                throw BusinessException.PARAM_INVALID;
            }

            // WebP 格式特殊校验
            if ("webp".equals(extension)) {
                if (header[0] != 'R' || header[1] != 'I' || header[2] != 'F' || header[3] != 'F') {
                    throw BusinessException.PARAM_INVALID;
                }
                byte[] webpHeader = new byte[12];
                try (InputStream is2 = file.getInputStream()) {
                    int webpRead = is2.read(webpHeader);
                    if (webpRead < 12) {
                        throw BusinessException.PARAM_INVALID;
                    }
                    if (!(webpHeader[8] == 'W' && webpHeader[9] == 'E' && webpHeader[10] == 'B' && webpHeader[11] == 'P')) {
                        throw BusinessException.PARAM_INVALID;
                    }
                }
                return;
            }

            // 比较魔数
            for (int i = 0; i < expectedMagic.length; i++) {
                if (header[i] != expectedMagic[i]) {
                    throw BusinessException.PARAM_INVALID;
                }
            }
        } catch (IOException e) {
            log.error("文件头校验异常: {}", e.getMessage());
            throw BusinessException.FILE_UPLOAD_FAILED;
        }
    }

    /**
     * 创建目录
     */
    private void createDirectory(String dirPath) {
        File dir = new File(dirPath);
        if (!dir.exists()) {
            boolean created = dir.mkdirs();
            if (!created) {
                log.error("目录创建失败: {}", dirPath);
                throw BusinessException.FILE_UPLOAD_FAILED;
            }
        }
    }

    /**
     * 检查文件扩展名是否允许
     */
    private boolean isAllowedImageType(String extension) {
        return Arrays.asList(getAllowedImageExtensions()).contains(extension.toLowerCase());
    }

    /**
     * 检查MIME类型是否允许
     */
    private boolean isAllowedMimeType(String contentType) {
        if (contentType == null) {
            return false;
        }
        return Arrays.asList(getAllowedMimeTypes()).contains(contentType.toLowerCase());
    }
}
