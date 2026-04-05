# 情侣私密菜单后端服务 Dockerfile
# 基于OpenJDK 17 多阶段构建

FROM maven:3.9-eclipse-temurin-17 AS builder

# 设置工作目录
WORKDIR /build

# 复制Maven相关文件
COPY pom.xml .
COPY src ./src

# 设置Maven镜像加速（阿里云）
RUN sed -i 's/repo.maven.apache.org/mirrors.aliyun.com/g' /etc/maven/settings.xml || true

# 下载依赖（利用缓存）
RUN mvn dependency:go-offline -B || true

# 构建项目
RUN mvn clean package -DskipTests

# 第二阶段：运行镜像
FROM eclipse-temurin:17-jre-alpine

# 设置时区
RUN apk add --no-cache tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' > /etc/timezone

# 安装必要的工具
RUN apk add --no-cache \
    curl \
    netcat-openbsd \
    redis-cli \
    mysql-client

# 创建应用目录
RUN mkdir -p /app/uploads /app/logs

# 从构建阶段复制jar文件
COPY --from=builder /build/target/*.jar /app/app.jar

# 设置环境变量
ENV JAVA_OPTS="-Xms512m -Xmx1024m -XX:+UseG1GC"
ENV SERVER_PORT=8080

# 创建entrypoint脚本
RUN echo '#!/bin/sh\n\
set -e\n\
\necho "Starting AI Couple Dish Backend..."\n\
\n# 等待MySQL就绪\necho "Waiting for MySQL..."\n\
until nc -z $DB_HOST $DB_PORT; do\n\
    echo "MySQL is unavailable - sleeping"\n\
    sleep 2\n\
done\n\
\necho "MySQL is up - continuing..."\n\
\n# 等待Redis就绪\necho "Waiting for Redis..."\n\
until nc -z $REDIS_HOST $REDIS_PORT; do\n\
    echo "Redis is unavailable - sleeping"\n\
    sleep 2\n\
done\n\
\necho "Redis is up - continuing..."\n\
\n# 启动应用\nexec java $JAVA_OPTS -jar /app/app.jar\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

WORKDIR /app

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/actuator/health || exit 1

# 运行入口脚本
ENTRYPOINT ["/app/entrypoint.sh"]
