#!/usr/bin/env bash
set -euo pipefail   
log() {  
    local level="${1:-INFO}"  
    local message="${2:-}"  
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")  
    echo “[$timestamp] [$level] $message”
}  
# 错误处理函数  
error_exit() {  
    log "ERROR" "\$1"  
    exit 1  
}  
# 部署脚本列表  
# DEPLOY_SCRIPTS=(  
#     "script/Manager.d.sol"  
#     "script/ManagerAddSource.s.sol"  
#     "script/SSC_Relay.d.sol"  
#     "script/BTC_Relay.d.sol"
#     "script/ETH_Relay.d.sol"  
#     "script/ManagerSetGenesis.s.sol"  
# )  
DEPLOY_SCRIPTS=(  
    "script/Manager.d.sol"  
    "script/ManagerAddSource.s.sol"  
    # "script/SEP_Relay.d.sol"  
    "script/BTC_Relay.d.sol"  
    "script/ManagerSetGenesis.s.sol"  
)  

# 主部署函数  
deploy_contracts() {    

    # 检查 RPC URL  
    if [ -z "$rpc_url" ]; then  
        error_exit "RPC URL 不能为空"  
    fi  

    log "INFO" "开始部署到 $env 环境"  
    log "INFO" "使用 RPC URL: $rpc_url"  

    # 遍历并部署脚本  
    for script in "${DEPLOY_SCRIPTS[@]}"; do  
        log "INFO" "正在部署: $script"  
        
        # 执行部署  
        DEPLOY_ENV="$env" \
        forge script "$script" \
            --rpc-url "$rpc_url" \
            --legacy \
            --broadcast || error_exit "部署 $script 失败"  
        
        log "INFO" "部署 $script 完成"  
    done  

    log "INFO" "所有合约部署成功"  
}  

# 主函数  
main() {  
    # 获取环境和 RPC URL（默认为 dev）  
    local env="${1:-dev}"  
    local rpc_url=""  

    # 检查 .env 文件是否存在  
    if [ -f .env ]; then  
        # shellcheck source=/dev/null  
        source .env  
    fi  

    # 如果第二个参数存在，使用第二个参数作为 RPC URL  
    if [ $# -eq 2 ]; then  
        # 修复 URL 格式  
        rpc_url="${2//:/://}"  
    fi  

    # 如果 RPC URL 为空，根据环境选择  
    if [ -z "$rpc_url" ]; then  
        case "$env" in  
            dev)  
                rpc_url="${DEV_RPC_URL}"  
                ;; 
            test)  
                rpc_url="${TEST_RPC_URL}"  
                ;; 
            prod)  
                rpc_url="${PROD_RPC_URL:-}"  
                ;;  
            *)  
                error_exit "不支持的环境: $env"  
                ;;  
        esac  
    fi  

    # 检查 RPC URL  
    if [ -z "$rpc_url" ]; then  
        error_exit "未找到 $env 环境的 RPC URL"  
    fi  

    # 开始部署  
    log "INFO" "开始部署流程..."  
    deploy_contracts "$env" "$rpc_url"  
    log "INFO" "部署流程完成"  
}  

# 捕获中断信号  
trap 'error_exit "部署过程被中断"' SIGINT SIGTERM  

# 执行主函数  
main "$@"  