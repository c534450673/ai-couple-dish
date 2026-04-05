package com.aicoupledish;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 情侣私密菜单 - 主启动类
 */
@EnableScheduling
@MapperScan("com.aicoupledish.dao.mapper")
@SpringBootApplication
public class AiCoupleDishApplication {

    public static void main(String[] args) {
        SpringApplication.run(AiCoupleDishApplication.class, args);
        System.out.println("========================================");
        System.out.println("  情侣私密菜单服务启动成功！");
        System.out.println("  API文档地址: http://localhost:8080/api/doc.html");
        System.out.println("========================================");
    }
}