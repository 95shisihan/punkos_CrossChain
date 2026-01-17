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

# 定义要运行的脚本 (注意这里改为 s.sol)
#RELAY_SCRIPT="script/SEP_Relay.s.sol"
RELAY_SCRIPT="script/BTC_Relay.s.sol"

run_relay() {
    # 检查 RPC URL
    if [ -z "${rpc_url:-}" ]; then
        error_exit "RPC URL 不能为空"
    fi

    log "INFO" "开始在 $env 环境运行中继脚本"
    log "INFO" "使用 RPC URL: $rpc_url"

    log "INFO" "正在执行: $RELAY_SCRIPT"

    # 这里的 PYTHON_PATH 是 s.sol 中需要的环境变量，需要确保 .env 里有或者在这里设置
    # 如果 s.sol 需要循环逻辑，这里只会执行一次 run() 然后退出
    DEPLOY_ENV="$env" \
    forge script "$RELAY_SCRIPT" \
        --rpc-url "$rpc_url" \
        --legacy \
        --broadcast \
        --with-gas-price 10000000000 \
        -vvvv || error_exit "运行 $RELAY_SCRIPT 失败"

    log "INFO" "$RELAY_SCRIPT 执行完成"
}

main() {
    # 默认环境为 dev
    local env="${1:-dev}" 
    # 定义变量用于接收 RPC
    local rpc_url=""

    # 加载 .env 文件
    if [ -f .env ]; then
        # shellcheck disable=SC1091
        source .env
    fi

    # 简单处理传入的第二个参数作为 RPC
    if [ $# -ge 2 ]; then
        rpc_url="$2"
    fi

    # 如果没有传入 RPC，根据环境自动获取
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

    if [ -z "$rpc_url" ]; then
        error_exit "未找到 $env 环境的 RPC URL"
    fi

    log "INFO" "开始中继流程..."
    run_relay
    log "INFO" "中继流程结束"
}

# 捕获中断信号
trap 'error_exit "运行过程被中断"' SIGINT SIGTERM

main "$@"
