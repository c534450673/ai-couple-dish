#!/bin/bash
#==============================================================================
# 情侣私密菜单 - 开发环境一键部署脚本
#==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}[开发环境部署]${NC}"

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  docker     Docker Compose部署"
    echo "  k8s        Kubernetes部署"
    echo "  build      构建Docker镜像"
    echo "  clean      清理资源"
    echo "  status     查看状态"
}

# Docker Compose部署
deploy_docker() {
    echo -e "${GREEN}[1]${NC} Docker Compose部署"
    cd "$DEPLOY_DIR/dev/docker"

    # 复制环境文件
    if [ ! -f .env ]; then
        cp .env.dev .env
        echo "已创建.env文件，请检查配置"
    fi

    # 构建并启动
    docker-compose up -d --build

    echo ""
    echo "服务启动中..."
    sleep 5

    # 显示状态
    docker-compose ps
    echo ""
    echo "访问地址:"
    echo "  API: http://localhost:8080/api"
    echo "  MySQL: localhost:3306"
    echo "  Redis: localhost:6379"
}

# Kubernetes部署
deploy_k8s() {
    echo -e "${GREEN}[2]${NC} Kubernetes部署"
    cd "$DEPLOY_DIR/dev/k8s"

    # 检查kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}kubectl未安装${NC}"
        exit 1
    fi

    # 部署
    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f backend.yaml

    echo ""
    echo "部署完成！"
    kubectl get pods -n ai-couple-dish-dev
}

# 构建镜像
build_image() {
    echo -e "${GREEN}[3]${NC} 构建Docker镜像"
    cd "$DEPLOY_DIR/../../backend"
    docker build -t registry.cn-hangzhou.aliyuncs.com/ai-couple-dish/backend:dev .
    echo "镜像构建完成"
}

# 清理
clean() {
    echo -e "${GREEN}[4]${NC} 清理资源"

    echo "清理Docker Compose..."
    cd "$DEPLOY_DIR/dev/docker"
    docker-compose down -v 2>/dev/null || true

    echo "清理Kubernetes..."
    cd "$DEPLOY_DIR/dev/k8s"
    kubectl delete -f backend.yaml -f secret.yaml -f configmap.yaml -f namespace.yaml 2>/dev/null || true

    echo "清理完成"
}

# 查看状态
status() {
    echo -e "${GREEN}[5]${NC} 查看状态"

    echo ""
    echo "Docker Compose:"
    cd "$DEPLOY_DIR/dev/docker" 2>/dev/null && docker-compose ps || echo "未在运行"

    echo ""
    echo "Kubernetes:"
    kubectl get pods -n ai-couple-dish-dev 2>/dev/null || echo "无法获取K8s状态"
}

# 主函数
case "${1:-}" in
    docker)
        deploy_docker
        ;;
    k8s)
        deploy_k8s
        ;;
    build)
        build_image
        ;;
    clean)
        clean
        ;;
    status)
        status
        ;;
    *)
        usage
        echo ""
        echo "示例: $0 docker"
        ;;
esac
