#!/bin/bash
#==============================================================================
# 情侣私密菜单 - 生产环境一键部署脚本
#==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         情侣私密菜单 - 生产环境部署                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

usage() {
    cat << EOF
用法: $0 [命令] [选项]

命令:
    build          构建并推送Docker镜像
    aliyun         部署到阿里云ACK
    tencent        部署到腾讯云TKE
    k8s            部署到自建Kubernetes
    check          检查配置
    status         查看状态

选项:
    -r, --registry REGISTRY    镜像仓库地址
    -t, --tag TAG              镜像标签 (默认: latest)
    -n, --namespace NAMESPACE  命名空间 (默认: ai-couple-dish-prod)

示例:
    # 构建并推送到阿里云
    $0 build -r registry.cn-hangzhou.aliyuncs.com/ai-couple-dish

    # 部署到阿里云ACK
    $0 aliyun -r registry.cn-hangzhou.aliyuncs.com/ai-couple-dish

    # 部署到自建K8s
    $0 k8s

EOF
}

# 检查前置条件
check_prerequisites() {
    echo -e "${BLUE}[检查]${NC} 前置条件..."

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker未安装${NC}"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}kubectl未安装${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} 前置条件检查通过"
}

# 检查配置
check_config() {
    echo -e "${BLUE}[检查]${NC} 生产环境配置..."
    echo ""

    # 检查Secrets
    echo "请确认以下配置已修改:"
    echo ""
    echo -e "${YELLOW}1. secret.yaml 中的密码和密钥:${NC}"
    echo "   - DB_PASSWORD"
    echo "   - REDIS_PASSWORD"
    echo "   - JWT_SECRET (至少32字符)"
    echo "   - WX_APPID / WX_SECRET"
    echo ""
    echo -e "${YELLOW}2. configmap.yaml 中的云服务地址:${NC}"
    echo "   - DB_HOST (云数据库地址)"
    echo "   - REDIS_HOST (云Redis地址)"
    echo ""

    read -p "是否继续部署? (y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "已取消"
        exit 0
    fi
}

# 构建镜像
build_image() {
    REGISTRY="${REGISTRY:-registry.cn-hangzhou.aliyuncs.com/ai-couple-dish}"
    TAG="${TAG:-latest}"

    echo -e "${BLUE}[构建]${NC} 构建Docker镜像..."
    echo "  仓库: $REGISTRY"
    echo "  标签: $TAG"
    echo ""

    cd "$PROJECT_ROOT/backend"

    # 构建
    docker build -t ${REGISTRY}/backend:${TAG} .
    docker tag ${REGISTRY}/backend:${TAG} ${REGISTRY}/backend:latest

    echo -e "${GREEN}✓${NC} 镜像构建完成"

    # 推送
    echo ""
    echo -e "${BLUE}[推送]${NC} 推送镜像..."

    # 登录镜像仓库
    echo "请确保已登录镜像仓库: docker login $REGISTRY"

    docker push ${REGISTRY}/backend:${TAG}
    docker push ${REGISTRY}/backend:latest

    echo -e "${GREEN}✓${NC} 镜像推送完成"
}

# 部署到阿里云ACK
deploy_aliyun() {
    REGISTRY="${REGISTRY:-registry.cn-hangzhou.aliyuncs.com/ai-couple-dish}"
    TAG="${TAG:-latest}"
    NAMESPACE="${NAMESPACE:-ai-couple-dish-prod}"

    echo -e "${BLUE}[阿里云ACK]${NC} 部署到阿里云..."
    echo "  仓库: $REGISTRY"
    echo "  标签: $TAG"
    echo ""

    check_prerequisites
    check_config

    # 更新镜像地址
    echo -e "${BLUE}[更新]${NC} 更新K8s配置中的镜像地址..."
    sed -i "s|image:.*|image: ${REGISTRY}/backend:${TAG}|g" "$DEPLOY_DIR/prod/k8s/backend.yaml"

    # 部署
    cd "$DEPLOY_DIR/prod/k8s"

    echo -e "${BLUE}[部署]${NC} 开始部署到namespace: $NAMESPACE"
    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f backend.yaml
    kubectl apply -f hpa.yaml

    echo ""
    echo -e "${GREEN}[完成]${NC} 部署完成！"
    echo ""
    echo "查看状态:"
    kubectl get pods -n $NAMESPACE
    kubectl get svc -n $NAMESPACE
    kubectl get ingress -n $NAMESPACE
}

# 部署到腾讯云TKE
deploy_tencent() {
    REGISTRY="${REGISTRY:-ccr.ccs.tencentyun.com/ai-couple-dish}"
    TAG="${TAG:-latest}"
    NAMESPACE="${NAMESPACE:-ai-couple-dish-prod}"

    echo -e "${BLUE}[腾讯云TKE]${NC} 部署到腾讯云..."
    echo "  仓库: $REGISTRY"
    echo "  标签: $TAG"
    echo ""

    check_prerequisites
    check_config

    # 更新镜像地址
    sed -i "s|image:.*|image: ${REGISTRY}/backend:${TAG}|g" "$DEPLOY_DIR/prod/k8s/backend.yaml"

    # 部署
    cd "$DEPLOY_DIR/prod/k8s"

    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f backend.yaml
    kubectl apply -f hpa.yaml

    echo -e "${GREEN}[完成]${NC} 部署完成！"
}

# 部署到自建K8s
deploy_k8s() {
    NAMESPACE="${NAMESPACE:-ai-couple-dish-prod}"

    echo -e "${BLUE}[自建K8s]${NC} 部署到Kubernetes..."
    echo ""

    check_prerequisites
    check_config

    cd "$DEPLOY_DIR/prod/k8s"

    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f backend.yaml
    kubectl apply -f hpa.yaml

    echo ""
    echo -e "${GREEN}[完成]${NC} 部署完成！"
    kubectl get pods -n $NAMESPACE
}

# 查看状态
status() {
    NAMESPACE="${NAMESPACE:-ai-couple-dish-prod}"

    echo -e "${BLUE}[状态]${NC} 查看生产环境状态..."
    echo ""

    echo "Pods:"
    kubectl get pods -n $NAMESPACE -o wide

    echo ""
    echo "Services:"
    kubectl get svc -n $NAMESPACE

    echo ""
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE

    echo ""
    echo "HPA:"
    kubectl get hpa -n $NAMESPACE
}

# 解析参数
REGISTRY=""
TAG="latest"
NAMESPACE="ai-couple-dish-prod"
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        build|aliyun|tencent|k8s|check|status)
            COMMAND="$1"
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# 执行命令
case $COMMAND in
    build)
        build_image
        ;;
    aliyun)
        deploy_aliyun
        ;;
    tencent)
        deploy_tencent
        ;;
    k8s)
        deploy_k8s
        ;;
    check)
        check_config
        ;;
    status)
        status
        ;;
    *)
        usage
        ;;
esac
