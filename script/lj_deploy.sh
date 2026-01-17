#!/usr/bin/env bash
set -euo pipefail

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

DEPLOY_SCRIPTS=(
    "script/Manager.d.sol"
    "script/ManagerAddSource.s.sol"
    "script/SEP_Relay.d.sol"
    "script/BTC_Relay.d.sol"
    "script/ManagerSetGenesis.s.sol"
)

deploy_contracts() {
    # 检查 RPC URL
    if [ -z "${rpc_url:-}" ]; then
        error_exit "RPC URL 不能为空"
    fi

    log "INFO" "开始部署到 $env 环境"
    log "INFO" "使用 RPC URL: $rpc_url"

    for script in "${DEPLOY_SCRIPTS[@]}"; do
        log "INFO" "正在部署: $script"

        DEPLOY_ENV="$env" \
        forge script "$script" \
            --rpc-url "$rpc_url" \
            --legacy \
            --broadcast \
            --with-gas-price 20000000000 || error_exit "部署 $script 失败"
            

        log "INFO" "部署 $script 完成"
    done

    log "INFO" "所有合约部署成功"
}

main() {
    local env="${1:-dev}"
    local rpc_url=""

    if [ -f .env ]; then
        # shellcheck disable=SC1091
        source .env
    fi

    if [ $# -eq 2 ]; then
        rpc_url="${2//:/://}"
    fi

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

    log "INFO" "开始部署流程..."
    deploy_contracts
    log "INFO" "部署流程完成"
}

trap 'error_exit "部署过程被中断"' SIGINT SIGTERM

main "$@"
