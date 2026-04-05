#!/bin/bash

#==========================================
# 情侣私密菜单 - 构建脚本
# 用于构建 H5 前端并复制到部署目录
#==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}构建 H5 前端...${NC}"

cd "$(dirname "$0")/frontend-h5"

# 安装依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}安装依赖...${NC}"
    npm install
fi

# 构建
echo -e "${YELLOW}构建生产版本...${NC}"
npm run build

# 复制到部署目录
echo -e "${YELLOW}复制构建产物到部署目录...${NC}"
mkdir -p ../deploy/lightweight/frontend-h5/dist
rm -rf ../deploy/lightweight/frontend-h5/dist/*
cp -r dist/* ../deploy/lightweight/frontend-h5/dist/

echo -e "${GREEN}构建完成！${NC}"
echo -e "构建产物位于: deploy/lightweight/frontend-h5/dist/"
