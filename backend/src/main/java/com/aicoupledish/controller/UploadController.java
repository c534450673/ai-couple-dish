package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.FileUploadResult;
import com.aicoupledish.service.FileService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.List;
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

    private final FileService fileService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    private static final int MAX_IMAGE_COUNT = 9;

    @ApiOperation("上传图片")
    @PostMapping("/image")
    public Result<Map<String, Object>> uploadImage(@RequestParam("file") MultipartFile file) {
        Long userId = getCurrentUserId(request, jwtUtils);

        if (file == null || file.isEmpty()) {
            return Result.badRequest("请选择要上传的文件");
        }

        FileUploadResult result = fileService.uploadImage(userId, file);

        Map<String, Object> response = new HashMap<>();
        response.put("url", result.getUrl());
        response.put("filename", result.getFilename());
        response.put("originalFilename", result.getOriginalFilename());
        response.put("size", result.getSize());
        response.put("type", result.getType());

        return Result.success("上传成功", response);
    }

    @ApiOperation("上传多张图片")
    @PostMapping("/images")
    public Result<Map<String, Object>> uploadImages(@RequestParam("files") MultipartFile[] files) {
        Long userId = getCurrentUserId(request, jwtUtils);

        if (files == null || files.length == 0) {
            return Result.badRequest("请选择要上传的文件");
        }

        if (files.length > MAX_IMAGE_COUNT) {
            return Result.badRequest("一次最多上传9张图片");
        }

        List<FileUploadResult> uploadedFiles = fileService.uploadImages(userId, files);

        Map<String, Object> result = new HashMap<>();
        result.put("files", uploadedFiles);
        result.put("count", uploadedFiles.size());

        return Result.success(result);
    }

    @ApiOperation("删除文件")
    @DeleteMapping("/file")
    public Result<Void> deleteFile(@RequestParam("fileKey") String fileKey) {
        Long userId = getCurrentUserId(request, jwtUtils);

        boolean deleted = fileService.deleteFile(userId, fileKey);

        if (deleted) {
            return Result.success("删除成功");
        } else {
            return Result.error("删除失败");
        }
    }
}
