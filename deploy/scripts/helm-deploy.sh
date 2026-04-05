#!/bin/bash
#==============================================================================
# 情侣私密菜单 - Helm一键部署脚本
#==============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

HELM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../helm/ai-couple-dish" && pwd)"
RELEASE_NAME="ai-couple-dish"
NAMESPACE="ai-couple-dish"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    install     安装Helm Chart
    upgrade     升级Helm Release
    uninstall   卸载Helm Release
    status      查看Release状态
    values      查看当前配置值

Options:
    -n, --namespace NAMESPACE    指定命名空间 (默认: ai-couple-dish)
    -r, --release RELEASE         指定Release名称 (默认: ai-couple-dish)
    -f, --values FILE             指定values文件
    --set KEY=VALUE              设置配置值

Examples:
    # 安装
    $0 install

    # 使用自定义values文件
    $0 install -f my-values.yaml

    # 设置特定值
    $0 install --set backend.replicaCount=4

    # 升级
    $0 upgrade

    # 卸载
    $0 uninstall

EOF
}

# 检查前置条件
check_prerequisites() {
    print_step "检查环境..."

    if ! command -v helm &> /dev/null; then
        print_error "Helm未安装，请先安装Helm"
        echo "安装命令: brew install helm"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl未安装"
        exit 1
    fi

    print_success "环境检查通过"
}

# 创建命名空间
create_namespace() {
    print_step "创建命名空间: $NAMESPACE"
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    print_success "命名空间创建完成"
}

# 安装Helm Chart
do_install() {
    check_prerequisites
    create_namespace

    print_step "安装Helm Chart..."

    CMD="helm install $RELEASE_NAME $HELM_DIR -n $NAMESPACE"

    if [ -n "$VALUES_FILE" ]; then
        CMD="$CMD -f $VALUES_FILE"
    fi

    if [ -n "$SET_VALUES" ]; then
        CMD="$CMD --set $SET_VALUES"
    fi

    eval $CMD

    print_success "Helm Chart安装完成！"
    echo ""
    echo "查看状态: helm status $RELEASE_NAME -n $NAMESPACE"
    echo "查看Pod: kubectl get pods -n $NAMESPACE"
    echo "查看服务: kubectl get svc -n $NAMESPACE"
}

# 升级Helm Release
do_upgrade() {
    check_prerequisites

    print_step "升级Helm Chart..."

    CMD="helm upgrade $RELEASE_NAME $HELM_DIR -n $NAMESPACE"

    if [ -n "$VALUES_FILE" ]; then
        CMD="$CMD -f $VALUES_FILE"
    fi

    if [ -n "$SET_VALUES" ]; then
        CMD="$CMD --set $SET_VALUES"
    fi

    eval $CMD

    print_success "Helm Chart升级完成！"
}

# 卸载Helm Release
do_uninstall() {
    print_step "卸载Helm Release..."
    helm uninstall $RELEASE_NAME -n $NAMESPACE
    print_success "卸载完成"
}

# 查看状态
do_status() {
    helm status $RELEASE_NAME -n $NAMESPACE
    echo ""
    kubectl get all -n $NAMESPACE
}

# 查看values
do_values() {
    helm show values $RELEASE_NAME $HELM_DIR
}

# 解析参数
VALUES_FILE=""
SET_VALUES=""
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        install|upgrade|uninstall|status|values)
            COMMAND="$1"
            shift
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        -f|--values)
            VALUES_FILE="$2"
            shift 2
            ;;
        --set)
            SET_VALUES="$2"
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

# 执行命令
case $COMMAND in
    install)
        do_install
        ;;
    upgrade)
        do_upgrade
        ;;
    uninstall)
        do_uninstall
        ;;
    status)
        do_status
        ;;
    values)
        do_values
        ;;
    *)
        if [ -z "$COMMAND" ]; then
            print_error "请指定命令"
            show_help
            exit 1
        fi
        ;;
esac
