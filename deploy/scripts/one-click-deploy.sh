#!/bin/bash
#==============================================================================
# 情侣私密菜单 - 一键上云脚本
# 支持: 阿里云ACK、腾讯云TKE、自建K8s
#==============================================================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           情侣私密菜单 - 容器化一键上云部署                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 显示菜单
show_menu() {
    echo ""
    echo "请选择部署平台:"
    echo ""
    echo "  ${GREEN}1${NC}. 阿里云 ACK (Container Service for Kubernetes)"
    echo "  ${GREEN}2${NC}. 腾讯云 TKE (Tencent Kubernetes Engine)"
    echo "  ${GREEN}3${NC}. Docker Compose (本地/轻量级)"
    echo "  ${GREEN}4${NC}. 自建 Kubernetes"
    echo "  ${GREEN}5${NC}. Helm Chart (通用K8s)"
    echo ""
    echo "  ${RED}0${NC}. 退出"
    echo ""
}

# 检查环境
check_env() {
    echo -e "${BLUE}[检查]${NC} 检查部署环境..."

    if command -v docker &> /dev/null; then
        echo "  ✓ Docker: $(docker --version | cut -d' ' -f3 | cut -c 2-)"
    fi

    if command -v kubectl &> /dev/null; then
        echo "  ✓ kubectl: $(kubectl version --client --short 2>/dev/null | cut -d' ' -f3)"
    fi

    if command -v helm &> /dev/null; then
        echo "  ✓ Helm: $(helm version --short 2>/dev/null | cut -d' ' -f2)"
    fi

    echo ""
}

# 阿里云ACK部署
deploy_aliyun() {
    echo -e "${GREEN}[1]${NC} 阿里云 ACK 部署"
    echo ""

    read -p "请输入镜像仓库地址 (默认: registry.cn-hangzhou.aliyuncs.com/ai-couple-dish): " REGISTRY
    REGISTRY=${REGISTRY:-registry.cn-hangzhou.aliyuncs.com/ai-couple-dish}

    read -p "请输入版本标签 (默认: latest): " TAG
    TAG=${TAG:-latest}

    echo -e "${BLUE}[执行]${NC} 构建并推送镜像..."
    cd "$PROJECT_ROOT/backend"

    # 构建镜像
    docker build -t ${REGISTRY}/backend:${TAG} .
    docker build -t ${REGISTRY}/backend:latest .

    # 推送镜像
    echo -e "${BLUE}[推送]${NC} 推送到阿里云镜像服务..."
    docker push ${REGISTRY}/backend:${TAG}
    docker push ${REGISTRY}/backend:latest

    # 更新K8s配置
    echo -e "${BLUE}[更新]${NC} 更新K8s配置..."
    sed -i "s|image:.*backend:.*|image: ${REGISTRY}/backend:${TAG}|g" \
        "$SCRIPT_DIR/k8s/backend.yaml"

    # 部署到K8s
    echo -e "${BLUE}[部署]${NC} 部署到Kubernetes..."
    cd "$SCRIPT_DIR/k8s"

    echo "请先修改 secret.yaml 中的密码配置！"
    echo ""

    read -p "是否继续部署? (y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "已取消部署"
        return
    fi

    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f mysql.yaml
    kubectl apply -f redis.yaml
    kubectl apply -f backend.yaml
    kubectl apply -f nginx.yaml
    kubectl apply -f ingress.yaml

    echo ""
    echo -e "${GREEN}[完成]${NC} 阿里云ACK部署完成！"
    echo "查看状态: kubectl get pods -n ai-couple-dish"
}

# 腾讯云TKE部署
deploy_tencent() {
    echo -e "${GREEN}[2]${NC} 腾讯云 TKE 部署"
    echo "功能开发中，请使用阿里云ACK或手动部署..."
}

# Docker Compose部署
deploy_docker() {
    echo -e "${GREEN}[3]${NC} Docker Compose 部署"
    echo ""

    cd "$SCRIPT_DIR/docker"

    # 检查.env文件
    if [ ! -f .env ]; then
        echo -e "${BLUE}[创建]${NC} 创建环境变量文件..."
        cp .env.example .env
        echo "请编辑 .env 文件配置密码！"
        read -p "是否继续? (y/n): " CONFIRM
        [ "$CONFIRM" != "y" ] && return
    fi

    echo -e "${BLUE}[构建]${NC} 构建并启动服务..."
    docker-compose up -d --build

    echo ""
    echo -e "${GREEN}[完成]${NC} Docker Compose部署完成！"
    echo ""
    echo "服务地址:"
    echo "  API: http://localhost:8080/api"
    echo "  MySQL: localhost:3306"
    echo "  Redis: localhost:6379"
    echo ""
    echo "查看日志: docker-compose logs -f"
}

# 自建K8s部署
deploy_k8s() {
    echo -e "${GREEN}[4]${NC} 自建 Kubernetes 部署"
    echo ""

    echo -e "${BLUE}[部署]${NC} 部署到Kubernetes..."

    cd "$SCRIPT_DIR/k8s"

    echo "请先修改 secret.yaml 中的密码配置！"
    read -p "是否继续? (y/n): " CONFIRM
    [ "$CONFIRM" != "y" ] && return

    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f mysql.yaml
    kubectl apply -f redis.yaml
    kubectl apply -f backend.yaml
    kubectl apply -f nginx.yaml
    kubectl apply -f ingress.yaml

    echo ""
    echo -e "${GREEN}[完成]${NC} Kubernetes部署完成！"
    echo "查看状态: kubectl get pods -n ai-couple-dish"
}

# Helm部署
deploy_helm() {
    echo -e "${GREEN}[5]${NC} Helm Chart 部署"
    echo ""

    if ! command -v helm &> /dev/null; then
        echo -e "${RED}[错误]${NC} Helm未安装！"
        echo "安装命令: brew install helm"
        return
    fi

    cd "$SCRIPT_DIR/scripts"
    chmod +x helm-deploy.sh

    echo "使用以下命令部署:"
    echo "  ./helm-deploy.sh install"
    echo ""
    echo "或指定配置:"
    echo "  ./helm-deploy.sh install -f /path/to/values.yaml"
}

# 主函数
main() {
    check_env

    while true; do
        show_menu
        read -p "请输入选项 [0-5]: " CHOICE

        case $CHOICE in
            1) deploy_aliyun; break ;;
            2) deploy_tencent; break ;;
            3) deploy_docker; break ;;
            4) deploy_k8s; break ;;
            5) deploy_helm; break ;;
            0) echo "退出"; exit 0 ;;
            *) echo -e "${RED}[错误]${NC} 无效选项，请重试" ;;
        esac
    done
}

main
