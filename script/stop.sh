#!/usr/bin/env bash
set -euo pipefail

# 日志函数
log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    local timestamp
    timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message"
}

# 错误处理函数
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# 定义要运行的 Solidity 脚本路径
# 对应上一条回答中创建的 Solidity 脚本文件名
#TARGET_SCRIPT="./script/StopChain.s.sol"
#恢复链和中继状态
TARGET_SCRIPT="./script/RunChain.s.sol"
run_deactivation() {
    # 检查 RPC URL
    if [ -z "${rpc_url:-}" ]; then
        error_exit "RPC URL 不能为空"
    fi

    log "INFO" "开始在 $env 环境执行源链禁用操作"
    log "INFO" "使用 RPC URL: $rpc_url"
    log "INFO" "正在执行脚本: $TARGET_SCRIPT"

    # 运行 Forge Script
    # DEPLOY_ENV 环境变量传递给 Solidity 脚本用于判断是 dev 还是 test
    DEPLOY_ENV="$env" \
    forge script "$TARGET_SCRIPT" \
        --rpc-url "$rpc_url" \
        --legacy \
        --broadcast \
        --with-gas-price 10000000000 \
        -vvvv || error_exit "运行 $TARGET_SCRIPT 失败"

    log "INFO" "$TARGET_SCRIPT 执行完成"
}

main() {
    # 1. 处理环境参数，默认为 dev
    local env="${1:-dev}" 
    # 定义变量用于接收 RPC
    local rpc_url=""

    # 2. 加载 .env 文件 (如果存在)
    if [ -f .env ]; then
        # shellcheck disable=SC1091
        source .env
    fi

    # 3. 处理命令行传入的第二个参数作为 RPC (可选)
    if [ $# -ge 2 ]; then
        rpc_url="$2"
    fi

    # 4. 如果没有传入 RPC，根据环境自动从 .env 变量中获取
    if [ -z "$rpc_url" ]; then
        case "$env" in
            dev)
                rpc_url="${DEV_RPC_URL:-}"
                ;;
            test)
                rpc_url="${TEST_RPC_URL:-}"
                ;;
            prod)
                rpc_url="${PROD_RPC_URL:-}"
                ;;
            *)
                error_exit "不支持的环境: $env"
                ;;
        esac
    fi

    # 5. 最终检查 RPC 是否获取成功
    if [ -z "$rpc_url" ]; then
        error_exit "未找到 $env 环境的 RPC URL，请检查 .env 文件配置"
    fi

    log "INFO" "准备禁用 BTC 链..."
    run_deactivation
    log "INFO" "操作流程结束"
}

# 捕获中断信号 (Ctrl+C)
trap 'error_exit "运行过程被中断"' SIGINT SIGTERM

# 执行主函数
main "$@"
