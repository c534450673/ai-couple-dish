# 情侣私密菜单后端服务 Dockerfile - 轻量级优化版
# 针对 2核4G 服务器优化

# 构建阶段
FROM maven:3.9-eclipse-temurin-17-alpine AS builder

WORKDIR /build

# 复制 Maven 相关文件
COPY pom.xml .
COPY src ./src

# Maven 镜像加速
RUN sed -i 's/repo.maven.apache.org/mirrors.aliyun.com/g' /etc/maven/settings.xml || true

# 构建项目
RUN mvn clean package -DskipTests -B

# 运行阶段 - 使用更小的基础镜像
FROM eclipse-temurin:17-jre-alpine

# 时区设置
RUN apk add --no-cache tzdata curl && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' > /etc/timezone

# 创建应用目录
RUN mkdir -p /app/uploads /app/logs

# 复制 jar 文件
COPY --from=builder /build/target/*.jar /app/app.jar

# 环境变量 - 针对 2核4G 优化的默认值
ENV JAVA_OPTS="-Xms384m -Xmx512m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
ENV SERVER_PORT=8080

WORKDIR /app

EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8080/api/actuator/health || exit 1

# 启动命令
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
