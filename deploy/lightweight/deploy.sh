#!/bin/bash

#==========================================
# 情侣私密菜单 - 一键部署脚本
# 适用于: 2核4G 服务器
#==========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  情侣私密菜单 - 轻量级部署${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker，请先安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker Compose，请先安装${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}未找到 .env 文件，从模板创建...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}请编辑 .env 文件配置必要参数后重新运行此脚本${NC}"
    echo -e "${YELLOW}必须修改: JWT_SECRET, WX_MINIAPP_APPID, WX_MINIAPP_SECRET${NC}"
    exit 1
fi

# 检查必要环境变量
source .env

if [ -z "$JWT_SECRET" ] || [[ "$JWT_SECRET" == *"change_me"* ]]; then
    echo -e "${RED}错误: 请在 .env 文件中设置 JWT_SECRET${NC}"
    exit 1
fi

# 检查 H5 前端是否已构建
if [ ! -d "frontend-h5/dist" ]; then
    echo -e "${YELLOW}H5 前端未构建，正在构建...${NC}"
    if [ -d "../frontend-h5" ]; then
        cd ../frontend-h5
        npm install
        npm run build
        mkdir -p ../deploy/lightweight/frontend-h5/dist
        cp -r dist/* ../deploy/lightweight/frontend-h5/dist/
        cd ../deploy/lightweight
    else
        echo -e "${RED}错误: 未找到 frontend-h5 目录${NC}"
    fi
fi

# 创建必要目录
mkdir -p nginx/ssl
mkdir -p frontend-h5/dist

# 部署命令
DEPLOY_CMD="docker-compose"
if docker compose version &> /dev/null; then
    DEPLOY_CMD="docker compose"
fi

echo -e "${GREEN}开始部署...${NC}"

# 停止旧容器
echo -e "${YELLOW}停止旧容器...${NC}"
$DEPLOY_CMD down --remove-orphans 2>/dev/null || true

# 构建并启动
echo -e "${YELLOW}构建镜像...${NC}"
$DEPLOY_CMD build --no-cache

echo -e "${YELLOW}启动服务...${NC}"
$DEPLOY_CMD up -d

# 等待服务就绪
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 10

# 检查服务状态
$DEPLOY_CMD ps

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址:"
echo -e "  H5 前端:  http://localhost"
echo -e "  API 文档: http://localhost/doc.html"
echo -e "  健康检查: http://localhost/api/actuator/health"
echo ""
echo -e "常用命令:"
echo -e "  查看日志:   $DEPLOY_CMD logs -f"
echo -e "  重启服务:   $DEPLOY_CMD restart"
echo -e "  停止服务:   $DEPLOY_CMD down"
echo ""
