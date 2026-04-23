package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.domain.dto.FileUploadResult;
import com.aicoupledish.service.impl.LocalFileStorageServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 本地文件存储服务单元测试
 * 测试范围：文件上传验证、文件存储、文件删除、URL生成、文件类型校验
 */
@DisplayName("本地文件存储服务测试")
class FileStorageServiceTest {

    private LocalFileStorageServiceImpl fileStorageService;

    @TempDir
    Path tempDir;

    @BeforeEach
    void setUp() {
        fileStorageService = new LocalFileStorageServiceImpl();
        ReflectionTestUtils.setField(fileStorageService, "uploadPath", tempDir.toString());
        ReflectionTestUtils.setField(fileStorageService, "baseUrl", "http://localhost:8080/api/uploads");
    }

    @Test
    @DisplayName("上传JPG图片-成功")
    void uploadImage_JpgSuccess() {
        // Given
        byte[] jpgHeader = new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF};
        byte[] jpgContent = new byte[jpgHeader.length + 10];
        System.arraycopy(jpgHeader, 0, jpgContent, 0, jpgHeader.length);
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.jpg",
            "image/jpeg",
            jpgContent
        );

        // When
        FileUploadResult result = fileStorageService.uploadImage(file);

        // Then
        assertNotNull(result);
        assertEquals("jpg", result.getType());
        assertTrue(result.getUrl().contains("http://localhost:8080/api/uploads"));
        assertTrue(result.getFilename().endsWith(".jpg"));
    }

    @Test
    @DisplayName("上传PNG图片-成功")
    void uploadImage_PngSuccess() {
        // Given - PNG文件头 (89 50 4E 47 0D 0A 1A 0A)
        byte[] pngHeader = new byte[]{(byte) 0x89, (byte) 0x50, (byte) 0x4E, (byte) 0x47, (byte) 0x0D, (byte) 0x0A, (byte) 0x1A, (byte) 0x0A};
        byte[] pngContent = new byte[pngHeader.length + 10];
        System.arraycopy(pngHeader, 0, pngContent, 0, pngHeader.length);
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.png",
            "image/png",
            pngContent
        );

        // When
        FileUploadResult result = fileStorageService.uploadImage(file);

        // Then
        assertNotNull(result);
        assertEquals("png", result.getType());
    }

    @Test
    @DisplayName("上传GIF图片-成功")
    void uploadImage_GifSuccess() {
        // Given - GIF文件头 (47 49 46)
        byte[] gifHeader = new byte[]{'G', 'I', 'F'};
        byte[] gifContent = new byte[gifHeader.length + 10];
        System.arraycopy(gifHeader, 0, gifContent, 0, gifHeader.length);
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.gif",
            "image/gif",
            gifContent
        );

        // When
        FileUploadResult result = fileStorageService.uploadImage(file);

        // Then
        assertNotNull(result);
        assertEquals("gif", result.getType());
    }

    @Test
    @DisplayName("上传空文件应抛异常")
    void uploadImage_EmptyFile_ShouldThrowException() {
        // Given
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "empty.jpg",
            "image/jpeg",
            new byte[0]
        );

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImage(file));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传null文件应抛异常")
    void uploadImage_NullFile_ShouldThrowException() {
        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImage(null));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传无效扩展名应抛异常")
    void uploadImage_InvalidExtension_ShouldThrowException() {
        // Given
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.exe",
            "application/octet-stream",
            "fake content".getBytes()
        );

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImage(file));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传无效MIME类型应抛异常")
    void uploadImage_InvalidMimeType_ShouldThrowException() {
        // Given
        byte[] jpgHeader = new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF};
        byte[] content = new byte[jpgHeader.length + 10];
        System.arraycopy(jpgHeader, 0, content, 0, jpgHeader.length);
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.jpg",
            "text/html",  // 错误的MIME类型
            content
        );

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImage(file));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传超过10MB的文件应抛异常")
    void uploadImage_FileTooLarge_ShouldThrowException() {
        // Given - 11MB file
        byte[] largeContent = new byte[11 * 1024 * 1024];
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "large.jpg",
            "image/jpeg",
            largeContent
        );

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImage(file));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传多张图片-成功")
    void uploadImages_Success() {
        // Given
        byte[] jpgHeader = new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF};
        byte[] jpgContent = new byte[jpgHeader.length + 10];
        System.arraycopy(jpgHeader, 0, jpgContent, 0, jpgHeader.length);

        byte[] pngHeader = new byte[]{(byte) 0x89, (byte) 0x50, (byte) 0x4E, (byte) 0x47, (byte) 0x0D, (byte) 0x0A, (byte) 0x1A, (byte) 0x0A};
        byte[] pngContent = new byte[pngHeader.length + 10];
        System.arraycopy(pngHeader, 0, pngContent, 0, pngHeader.length);

        MockMultipartFile file1 = new MockMultipartFile("file", "test1.jpg", "image/jpeg", jpgContent);
        MockMultipartFile file2 = new MockMultipartFile("file", "test2.png", "image/png", pngContent);
        MultipartFile[] files = {file1, file2};

        // When
        List<FileUploadResult> results = fileStorageService.uploadImages(files);

        // Then
        assertNotNull(results);
        assertEquals(2, results.size());
    }

    @Test
    @DisplayName("上传超过9张图片应抛异常")
    void uploadImages_TooManyFiles_ShouldThrowException() {
        // Given
        byte[] content = "test".getBytes();
        MultipartFile[] files = new MultipartFile[10];
        for (int i = 0; i < 10; i++) {
            files[i] = new MockMultipartFile("file", "test" + i + ".jpg", "image/jpeg", content);
        }

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImages(files));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传空数组应抛异常")
    void uploadImages_EmptyArray_ShouldThrowException() {
        // Given
        MultipartFile[] files = new MultipartFile[0];

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImages(files));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("上传null数组应抛异常")
    void uploadImages_NullArray_ShouldThrowException() {
        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> fileStorageService.uploadImages(null));
        assertEquals(BusinessException.PARAM_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("删除存在的文件-成功")
    void deleteFile_ExistingFile_ShouldReturnTrue() {
        // Given - First upload a file
        byte[] jpgHeader = new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF};
        byte[] jpgContent = new byte[jpgHeader.length + 10];
        System.arraycopy(jpgHeader, 0, jpgContent, 0, jpgHeader.length);
        MockMultipartFile file = new MockMultipartFile("file", "test.jpg", "image/jpeg", jpgContent);
        FileUploadResult result = fileStorageService.uploadImage(file);
        String fileKey = result.getFileKey();

        // When
        boolean deleteResult = fileStorageService.deleteFile(fileKey);

        // Then
        assertTrue(deleteResult);
    }

    @Test
    @DisplayName("删除不存在的文件应返回false")
    void deleteFile_NonExistingFile_ShouldReturnFalse() {
        // Given
        String nonExistingKey = "2024/01/01/nonexistent.jpg";

        // When
        boolean result = fileStorageService.deleteFile(nonExistingKey);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("删除空key应返回false")
    void deleteFile_EmptyKey_ShouldReturnFalse() {
        // When & Then
        assertFalse(fileStorageService.deleteFile(null));
        assertFalse(fileStorageService.deleteFile(""));
    }

    @Test
    @DisplayName("获取文件URL-成功")
    void getFileUrl_Success() {
        // Given
        String fileKey = "2024/01/01/test.jpg";

        // When
        String url = fileStorageService.getFileUrl(fileKey);

        // Then
        assertEquals("http://localhost:8080/api/uploads/2024/01/01/test.jpg", url);
    }

    @Test
    @DisplayName("获取文件URL-空key应返回null")
    void getFileUrl_EmptyKey_ShouldReturnNull() {
        // When & Then
        assertNull(fileStorageService.getFileUrl(null));
        assertNull(fileStorageService.getFileUrl(""));
    }

    @Test
    @DisplayName("检查是否为图片-JPG应返回true")
    void isImage_Jpg_ShouldReturnTrue() {
        // Given
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.jpg",
            "image/jpeg",
            "content".getBytes()
        );

        // When
        boolean result = fileStorageService.isImage(file);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("检查是否为图片-PNG应返回true")
    void isImage_Png_ShouldReturnTrue() {
        // Given
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.png",
            "image/png",
            "content".getBytes()
        );

        // When
        boolean result = fileStorageService.isImage(file);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("检查是否为图片-非图片应返回false")
    void isImage_NonImage_ShouldReturnFalse() {
        // Given
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.exe",
            "application/octet-stream",
            "content".getBytes()
        );

        // When
        boolean result = fileStorageService.isImage(file);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("检查是否为图片-null应返回false")
    void isImage_Null_ShouldReturnFalse() {
        // When & Then
        assertFalse(fileStorageService.isImage(null));
    }

    @Test
    @DisplayName("检查是否为图片-空文件应返回false")
    void isImage_EmptyFile_ShouldReturnFalse() {
        // Given
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "test.jpg",
            "image/jpeg",
            new byte[0]
        );

        // When
        boolean result = fileStorageService.isImage(file);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("允许的图片扩展名包含jpg")
    void getAllowedImageExtensions_ShouldContainJpg() {
        // When
        String[] extensions = fileStorageService.getAllowedImageExtensions();

        // Then
        assertContains(extensions, "jpg");
        assertContains(extensions, "jpeg");
        assertContains(extensions, "png");
        assertContains(extensions, "gif");
        assertContains(extensions, "webp");
    }

    @Test
    @DisplayName("允许的MIME类型包含jpeg")
    void getAllowedMimeTypes_ShouldContainJpeg() {
        // When
        String[] mimeTypes = fileStorageService.getAllowedMimeTypes();

        // Then
        assertContains(mimeTypes, "image/jpeg");
        assertContains(mimeTypes, "image/png");
        assertContains(mimeTypes, "image/gif");
        assertContains(mimeTypes, "image/webp");
    }

    @Test
    @DisplayName("最大文件大小应为10MB")
    void getMaxFileSize_ShouldBe10MB() {
        // When
        long maxSize = fileStorageService.getMaxFileSize();

        // Then
        assertEquals(10 * 1024 * 1024, maxSize);
    }

    private void assertContains(String[] array, String value) {
        boolean found = false;
        for (String item : array) {
            if (item.equals(value)) {
                found = true;
                break;
            }
        }
        assertTrue(found, "Array should contain: " + value);
    }
}
