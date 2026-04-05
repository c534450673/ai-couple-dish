#!/bin/bash
#==============================================================================
# 情侣私密菜单 - 一键部署脚本
# 支持本地Docker Compose部署和阿里云/腾讯云ACK部署
#==============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"

# 默认配置
DEPLOY_MODE="docker"  # docker | k8s | aliyun | tencent
BACKEND_VERSION="latest"
MYSQL_PASSWORD="aicoupledish_pass"
REDIS_PASSWORD="redis_pass"
DOMAIN="api.aicoupledish.com"

# 打印函数
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 帮助信息
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -m, --mode MODE          部署模式: docker, k8s, aliyun, tencent
    -v, --version VERSION    后端版本 (默认: latest)
    -d, --domain DOMAIN      API域名 (默认: api.aicoupledish.com)
    --mysql-pass PASSWORD    MySQL密码
    --redis-pass PASSWORD    Redis密码
    -h, --help              显示帮助信息

Examples:
    # 本地Docker Compose部署
    $0 -m docker

    # 阿里云ACK部署
    $0 -m aliyun -d api.example.com

    # 腾讯云TKE部署
    $0 -m tencent -v 1.0.0

EOF
}

# 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                DEPLOY_MODE="$2"
                shift 2
                ;;
            -v|--version)
                BACKEND_VERSION="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            --mysql-pass)
                MYSQL_PASSWORD="$2"
                shift 2
                ;;
            --redis-pass)
                REDIS_PASSWORD="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检查前置条件
check_prerequisites() {
    print_step "检查部署环境..."

    case $DEPLOY_MODE in
        docker)
            if ! command -v docker &> /dev/null; then
                print_error "Docker 未安装，请先安装 Docker"
                exit 1
            fi
            if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
                print_error "Docker Compose 未安装"
                exit 1
            fi
            print_success "Docker 环境检查通过"
            ;;
        k8s)
            if ! command -v kubectl &> /dev/null; then
                print_error "kubectl 未安装"
                exit 1
            fi
            if ! command -v helm &> /dev/null; then
                print_warning "Helm 未安装，部分功能可能不可用"
            fi
            print_success "Kubernetes 环境检查通过"
            ;;
        aliyun|tencent)
            if ! command -v kubectl &> /dev/null; then
                print_error "kubectl 未安装"
                exit 1
            fi
            if ! command -v terraform &> /dev/null; then
                print_warning "Terraform 未安装，无法自动创建基础设施"
            fi
            print_success "云环境工具检查通过"
            ;;
    esac
}

# 准备环境变量
prepare_env() {
    print_step "准备环境变量..."

    export MYSQL_PASSWORD
    export REDIS_PASSWORD
    export DOMAIN
    export BACKEND_VERSION

    # 创建.env文件（如果不存在）
    if [ ! -f "${DEPLOY_DIR}/docker/.env" ]; then
        cat > "${DEPLOY_DIR}/docker/.env" << EOF
# 数据库配置
MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD}
MYSQL_DATABASE=ai_couple_dish
MYSQL_USER=aicoupledish
MYSQL_PASSWORD=${MYSQL_PASSWORD}

# Redis配置
REDIS_PASSWORD=${REDIS_PASSWORD}

# API配置
API_PORT=8080
NGINX_PORT=80
NGINX_SSL_PORT=443

# 微信小程序配置（请修改为实际值）
WX_APPID=your-appid
WX_SECRET=your-secret

# JWT配置
JWT_SECRET=aiCoupleDishSecretKey2024VeryLongAndSecureForProduction
EOF
        print_success "环境变量文件已创建: ${DEPLOY_DIR}/docker/.env"
    else
        print_warning "环境变量文件已存在，跳过创建"
    fi
}

# 构建Docker镜像
build_image() {
    print_step "构建Docker镜像..."

    cd "${PROJECT_ROOT}/backend"

    # 获取版本号
    if [ "$BACKEND_VERSION" == "latest" ]; then
        BACKEND_VERSION=$(git describe --tags --always 2>/dev/null || echo "dev")
    fi

    # 构建镜像
    docker build \
        --build-arg BUILD_TIME=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
        -t ai-couple-dish-backend:${BACKEND_VERSION} \
        -t ai-couple-dish-backend:latest \
        .

    print_success "镜像构建完成: ai-couple-dish-backend:${BACKEND_VERSION}"
}

# Docker Compose部署
deploy_docker() {
    print_step "使用Docker Compose部署..."

    cd "${DEPLOY_DIR}/docker"

    # 拉取最新镜像（如果使用latest）
    docker-compose pull

    # 启动服务
    docker-compose up -d

    # 等待服务启动
    print_step "等待服务启动..."
    sleep 10

    # 检查服务状态
    docker-compose ps

    # 显示日志
    print_success "部署完成！查看日志: docker-compose logs -f backend"
}

# Kubernetes部署
deploy_k8s() {
    print_step "使用Kubernetes部署..."

    cd "${DEPLOY_DIR}/k8s"

    # 应用配置
    kubectl apply -f namespace.yaml
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    kubectl apply -f mysql.yaml
    kubectl apply -f redis.yaml
    kubectl apply -f backend.yaml
    kubectl apply -f nginx.yaml

    # 等待部署完成
    print_step "等待Pod启动..."
    kubectl rollout status deployment/backend -n ai-couple-dish
    kubectl rollout status deployment/mysql -n ai-couple-dish
    kubectl rollout status deployment/redis -n ai-couple-dish

    print_success "Kubernetes部署完成！"
    print_step "获取服务状态: kubectl get pods -n ai-couple-dish"
}

# 阿里云ACK部署
deploy_aliyun() {
    print_step "部署到阿里云ACK..."

    # 检查阿里云CLI
    if ! command -v aliyun &> /dev/null; then
        print_error "阿里云CLI未安装"
        exit 1
    fi

    # 登录容器镜像服务
    print_step "登录阿里云镜像服务..."
    aliyun cr Login --endpoint registry.cn-hangzhou.aliyuncs.com

    # 构建并推送镜像
    print_step "构建并推送镜像到阿里云..."
    cd "${PROJECT_ROOT}/backend"

    REGISTRY="registry.cn-hangzhou.aliyuncs.com/ai-couple-dish"
    docker build -t ${REGISTRY}/backend:${BACKEND_VERSION} .
    docker push ${REGISTRY}/backend:${BACKEND_VERSION}

    # 更新K8s配置中的镜像地址
    sed -i "s|image:.*backend:.*|image: ${REGISTRY}/backend:${BACKEND_VERSION}|g" \
        "${DEPLOY_DIR}/k8s/backend.yaml"

    # 部署到ACK
    deploy_k8s

    print_success "阿里云ACK部署完成！"
}

# 腾讯云TKE部署
deploy_tencent() {
    print_step "部署到腾讯云TKE..."

    # 检查腾讯云CLI
    if ! command -v tccli &> /dev/null; then
        print_error "腾讯云CLI未安装"
        exit 1
    fi

    # 登录容器镜像
    print_step "登录腾讯云镜像服务..."
    ccr Login -u $TCCLoud_SecretId -p $TCCLoud_SecretKey

    # 构建并推送镜像
    print_step "构建并推送镜像到腾讯云..."
    cd "${PROJECT_ROOT}/backend"

    REGISTRY="ccr.ccs.tencentyun.com/ai-couple-dish"
    docker build -t ${REGISTRY}/backend:${BACKEND_VERSION} .
    docker push ${REGISTRY}/backend:${BACKEND_VERSION}

    # 更新K8s配置
    sed -i "s|image:.*backend:.*|image: ${REGISTRY}/backend:${BACKEND_VERSION}|g" \
        "${DEPLOY_DIR}/k8s/backend.yaml"

    # 部署到TKE
    deploy_k8s

    print_success "腾讯云TKE部署完成！"
}

# 健康检查
health_check() {
    print_step "执行健康检查..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:8080/api/actuator/health > /dev/null 2>&1; then
            print_success "健康检查通过！"
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "健康检查失败，请检查服务日志"
    return 1
}

# 清理函数
cleanup() {
    print_step "清理临时文件..."
    cd "${PROJECT_ROOT}"
    # 删除临时文件
    find . -name "*.tmp" -delete 2>/dev/null || true
    print_success "清理完成"
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  情侣私密菜单 - 一键部署脚本"
    echo "========================================"
    echo ""

    # 解析参数
    parse_args "$@"

    # 检查前置条件
    check_prerequisites

    # 准备环境
    prepare_env

    # 根据部署模式执行
    case $DEPLOY_MODE in
        docker)
            build_image
            deploy_docker
            health_check
            ;;
        k8s)
            build_image
            deploy_k8s
            ;;
        aliyun)
            deploy_aliyun
            ;;
        tencent)
            deploy_tencent
            ;;
        *)
            print_error "不支持的部署模式: $DEPLOY_MODE"
            exit 1
            ;;
    esac

    # 清理
    cleanup

    echo ""
    echo "========================================"
    print_success "部署完成！"
    echo "========================================"
    echo ""
    echo "后续步骤:"
    echo "  1. 配置域名DNS解析"
    echo "  2. 申请并配置SSL证书"
    echo "  3. 配置微信小程序后台服务器域名"
    echo "  4. 查看日志: docker-compose logs -f"
    echo ""
}

# 脚本入口
main "$@"
