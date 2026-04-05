package com.aicoupledish.controller;

import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.StrUtil;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.servlet.http.HttpServletRequest;
import java.io.File;
import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * 文件上传控制器
 */
@Slf4j
@Api(tags = "文件上传模块")
@RestController
@RequestMapping("/upload")
@RequiredArgsConstructor
public class UploadController extends BaseAuthController {

    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @Value("${file.upload.path:/app/uploads}")
    private String uploadPath;

    @Value("${file.upload.base-url:http://localhost:8080/api/uploads}")
    private String baseUrl;

    // 允许的图片类型
    private static final String[] ALLOWED_IMAGE_TYPES = {"jpg", "jpeg", "png", "gif", "webp"};

    // 最大文件大小 10MB
    private static final long MAX_FILE_SIZE = 10 * 1024 * 1024;

    @ApiOperation("上传图片")
    @PostMapping("/image")
    public Result<Map<String, Object>> uploadImage(@RequestParam("file") MultipartFile file) {
        // 验证文件
        if (file == null || file.isEmpty()) {
            return Result.error(400, "请选择要上传的文件");
        }

        // 验证文件大小
        if (file.getSize() > MAX_FILE_SIZE) {
            return Result.error(400, "文件大小不能超过10MB");
        }

        // 获取原始文件名和扩展名
        String originalFilename = file.getOriginalFilename();
        if (StrUtil.isBlank(originalFilename)) {
            return Result.error(400, "文件名不能为空");
        }

        String extension = FileUtil.extName(originalFilename).toLowerCase();

        // 验证文件类型
        if (!isAllowedImageType(extension)) {
            return Result.error(400, "只支持 jpg, jpeg, png, gif, webp 格式的图片");
        }

        try {
            // 生成新文件名
            String newFilename = IdUtil.simpleUUID() + "." + extension;

            // 按日期创建目录
            String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
            String dirPath = uploadPath + File.separator + datePath;

            // 创建目录
            File dir = new File(dirPath);
            if (!dir.exists()) {
                dir.mkdirs();
            }

            // 保存文件
            File destFile = new File(dirPath + File.separator + newFilename);
            file.transferTo(destFile);

            // 构建返回结果
            String relativePath = datePath + "/" + newFilename;
            String fileUrl = baseUrl + "/" + relativePath;

            Map<String, Object> result = new HashMap<>();
            result.put("url", fileUrl);
            result.put("filename", newFilename);
            result.put("originalFilename", originalFilename);
            result.put("size", file.getSize());
            result.put("type", extension);

            log.info("文件上传成功: userId={}, file={}", getCurrentUserId(request, jwtUtils), fileUrl);

            return Result.success("上传成功", result);
        } catch (IOException e) {
            log.error("文件上传失败: {}", e.getMessage(), e);
            return Result.error(500, "文件上传失败: " + e.getMessage());
        }
    }

    @ApiOperation("上传多张图片")
    @PostMapping("/images")
    public Result<Map<String, Object>> uploadImages(@RequestParam("files") MultipartFile[] files) {
        if (files == null || files.length == 0) {
            return Result.error(400, "请选择要上传的文件");
        }

        if (files.length > 9) {
            return Result.error(400, "一次最多上传9张图片");
        }

        Map<String, Object> result = new HashMap<>();
        java.util.List<Map<String, Object>> uploadedFiles = new java.util.ArrayList<>();

        for (MultipartFile file : files) {
            Result<Map<String, Object>> uploadResult = uploadImage(file);
            if (uploadResult.getCode() == 200) {
                uploadedFiles.add(uploadResult.getData());
            }
        }

        result.put("files", uploadedFiles);
        result.put("count", uploadedFiles.size());

        return Result.success(result);
    }

    private boolean isAllowedImageType(String extension) {
        for (String type : ALLOWED_IMAGE_TYPES) {
            if (type.equalsIgnoreCase(extension)) {
                return true;
            }
        }
        return false;
    }

}
