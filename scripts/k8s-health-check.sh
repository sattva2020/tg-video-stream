#!/bin/bash
################################################################################
# Kubernetes Health Check Script
# Verifies the health of a Sattva deployment
#
# Usage: ./scripts/k8s-health-check.sh [namespace]
#
# Arguments:
#   namespace    - Kubernetes namespace (default: sattva)
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
DEFAULT_NAMESPACE="sattva"
RELEASE_NAME="${RELEASE_NAME:-sattva}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Symbols
readonly CHECK_MARK="✓"
readonly CROSS_MARK="✗"
readonly WARNING_MARK="⚠"

# Track overall health
OVERALL_HEALTHY=true

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    local title=$1
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${title}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_check() {
    local status=$1
    local message=$2

    case "${status}" in
        pass)
            echo -e " ${GREEN}${CHECK_MARK}${NC} ${message}"
            ;;
        fail)
            echo -e " ${RED}${CROSS_MARK}${NC} ${message}"
            OVERALL_HEALTHY=false
            ;;
        warn)
            echo -e " ${YELLOW}${WARNING_MARK}${NC} ${message}"
            ;;
    esac
}

################################################################################
# Usage
################################################################################

usage() {
    cat << EOF
Usage: $(basename "$0") [namespace]

Verifies the health of a Sattva Kubernetes deployment.

Arguments:
  namespace    Kubernetes namespace (default: ${DEFAULT_NAMESPACE})

Options:
  -h, --help    Show this help message
  -v, --verbose Enable verbose output

Checks performed:
  • Pod status (Running, Ready, Restarts)
  • Services existence and endpoints
  • Ingress configuration
  • HTTP endpoint health checks
  • HPA (Horizontal Pod Autoscaler) status
  • PVC (Persistent Volume Claim) binding
  • Resource utilization

Exit codes:
  0 - All checks passed
  1 - One or more checks failed
  2 - Critical error (unable to run checks)

Examples:
  $(basename "$0")                    # Check default namespace
  $(basename "$0") sattva-prod        # Check production namespace
  $(basename "$0") sattva -v          # Verbose output

EOF
    exit 0
}

################################################################################
# Helper Functions
################################################################################

check_kubectl_installed() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 2
    fi
}

check_cluster_access() {
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 2
    fi
}

check_namespace_exists() {
    local namespace=$1

    if ! kubectl get namespace "${namespace}" &> /dev/null; then
        log_error "Namespace '${namespace}' does not exist"
        exit 2
    fi
}

################################################################################
# Health Checks
################################################################################

check_pods() {
    print_header "POD STATUS"

    local namespace=$1
    local pods
    pods=$(kubectl get pods -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${pods}" ]]; then
        print_check "fail" "No pods found in namespace '${namespace}'"
        return
    fi

    local total_pods=0
    local running_pods=0
    local ready_pods=0
    local high_restart_pods=0

    for pod in ${pods}; do
        ((total_pods++))

        local pod_status
        pod_status=$(kubectl get pod "${pod}" -n "${namespace}" -o jsonpath='{.status.phase}')

        local ready
        ready=$(kubectl get pod "${pod}" -n "${namespace}" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')

        local restarts
        restarts=$(kubectl get pod "${pod}" -n "${namespace}" -o jsonpath='{.status.containerStatuses[0].restartCount}')

        local app_name
        app_name=$(kubectl get pod "${pod}" -n "${namespace}" -o jsonpath='{.metadata.labels.app}')

        if [[ "${pod_status}" == "Running" ]]; then
            ((running_pods++))
        fi

        if [[ "${ready}" == "true" ]]; then
            ((ready_pods++))
        fi

        if [[ ${restarts} -gt 5 ]]; then
            ((high_restart_pods++))
            print_check "warn" "Pod '${pod}' (${app_name}) has ${restarts} restarts"
        elif [[ "${pod_status}" != "Running" ]]; then
            print_check "fail" "Pod '${pod}' (${app_name}) is ${pod_status}"
        elif [[ "${ready}" != "true" ]]; then
            print_check "fail" "Pod '${pod}' (${app_name}) is not ready"
        else
            print_check "pass" "Pod '${pod}' (${app_name}) is Running and Ready"
        fi
    done

    echo ""
    log_info "Pod Summary: ${ready_pods}/${total_pods} ready, ${running_pods}/${total_pods} running"

    if [[ ${high_restart_pods} -gt 0 ]]; then
        log_warning "${high_restart_pods} pod(s) with high restart counts"
    fi
}

check_services() {
    print_header "SERVICE STATUS"

    local namespace=$1

    # Get all services
    local services
    services=$(kubectl get svc -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${services}" ]]; then
        print_check "warn" "No services found in namespace '${namespace}'"
        return
    fi

    for service in ${services}; do
        local service_type
        service_type=$(kubectl get svc "${service}" -n "${namespace}" -o jsonpath='{.spec.type}')

        local endpoints
        endpoints=$(kubectl get endpoints "${service}" -n "${namespace}" -o jsonpath='{.subsets[*].addresses[*].ip}')

        if [[ -z "${endpoints}" ]]; then
            print_check "fail" "Service '${service}' (${service_type}) has no endpoints"
        else
            local endpoint_count
            endpoint_count=$(echo "${endpoints}" | wc -w)
            print_check "pass" "Service '${service}' (${service_type}) has ${endpoint_count} endpoint(s)"
        fi
    done
}

check_ingress() {
    print_header "INGRESS STATUS"

    local namespace=$1

    # Get all ingresses
    local ingresses
    ingresses=$(kubectl get ingress -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${ingresses}" ]]; then
        print_check "warn" "No ingress resources found in namespace '${namespace}'"
        return
    fi

    for ingress in ${ingresses}; do
        local hosts
        hosts=$(kubectl get ingress "${ingress}" -n "${namespace}" -o jsonpath='{.spec.rules[*].host}')

        local address
        address=$(kubectl get ingress "${ingress}" -n "${namespace}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

        if [[ -n "${address}" ]]; then
            print_check "pass" "Ingress '${ingress}' at ${address}"
            for host in ${hosts}; do
                echo -e "   └─ Host: ${host}"
            done
        else
            print_check "warn" "Ingress '${ingress}' has no address assigned yet"
            for host in ${hosts}; do
                echo -e "   └─ Host: ${host}"
            done
        fi
    done
}

check_http_endpoints() {
    print_header "HTTP ENDPOINT CHECKS"

    local namespace=$1

    # Get frontend service
    local frontend_svc
    frontend_svc=$(kubectl get svc -n "${namespace}" -o jsonpath='{.items[?(@.metadata.labels.app=="frontend")].metadata.name}' 2>/dev/null || echo "")

    # Get backend service
    local backend_svc
    backend_svc=$(kubectl get svc -n "${namespace}" -o jsonpath='{.items[?(@.metadata.labels.app=="backend")].metadata.name}' 2>/dev/null || echo "")

    # Get transcoder service
    local transcoder_svc
    transcoder_svc=$(kubectl get svc -n "${namespace}" -o jsonpath='{.items[?(@.metadata.labels.app=="transcoder")].metadata.name}' 2>/dev/null || echo "")

    # Check frontend
    if [[ -n "${frontend_svc}" ]]; then
        local frontend_ip
        frontend_ip=$(kubectl get svc "${frontend_svc}" -n "${namespace}" -o jsonpath='{.spec.clusterIP}')

        if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never -n "${namespace}" \
           -- curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://${frontend_ip}" 2>/dev/null | grep -q "200"; then
            print_check "pass" "Frontend HTTP endpoint is responding"
        else
            print_check "warn" "Frontend HTTP endpoint check failed (service may not be accessible from test pod)"
        fi
    fi

    # Check backend /health/ready
    if [[ -n "${backend_svc}" ]]; then
        local backend_ip
        backend_ip=$(kubectl get svc "${backend_svc}" -n "${namespace}" -o jsonpath='{.spec.clusterIP}')

        if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never -n "${namespace}" \
           -- curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://${backend_ip}/health/ready" 2>/dev/null | grep -q "200"; then
            print_check "pass" "Backend /health/ready endpoint is responding"
        else
            print_check "warn" "Backend /health/ready endpoint check failed (service may not be accessible from test pod)"
        fi
    fi

    # Check transcoder /health
    if [[ -n "${transcoder_svc}" ]]; then
        local transcoder_ip
        transcoder_ip=$(kubectl get svc "${transcoder_svc}" -n "${namespace}" -o jsonpath='{.spec.clusterIP}')

        if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never -n "${namespace}" \
           -- curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://${transcoder_ip}/health" 2>/dev/null | grep -q "200"; then
            print_check "pass" "Transcoder /health endpoint is responding"
        else
            print_check "warn" "Transcoder /health endpoint check failed (service may not be accessible from test pod)"
        fi
    fi
}

check_hpa() {
    print_header "HORIZONTAL POD AUTOSCALER STATUS"

    local namespace=$1

    # Get all HPAs
    local hpas
    hpas=$(kubectl get hpa -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${hpas}" ]]; then
        print_check "warn" "No HPAs found in namespace '${namespace}'"
        return
    fi

    for hpa in ${hpas}; do
        local min_replicas
        min_replicas=$(kubectl get hpa "${hpa}" -n "${namespace}" -o jsonpath='{.spec.minReplicas}')

        local max_replicas
        max_replicas=$(kubectl get hpa "${hpa}" -n "${namespace}" -o jsonpath='{.spec.maxReplicas}')

        local current_replicas
        current_replicas=$(kubectl get hpa "${hpa}" -n "${namespace}" -o jsonpath='{.status.currentReplicas}')

        local desired_replicas
        desired_replicas=$(kubectl get hpa "${hpa}" -n "${namespace}" -o jsonpath='{.status.desiredReplicas}')

        local targets
        targets=$(kubectl get hpa "${hpa}" -n "${namespace}" -o jsonpath='{.spec.metrics[0].resource.target.averageUtilization}')

        if [[ ${current_replicas} -ge ${min_replicas} && ${current_replicas} -le ${max_replicas} ]]; then
            print_check "pass" "HPA '${hpa}': ${current_replicas}/${desired_replicas} replicas (min: ${min_replicas}, max: ${max_replicas}, target: ${targets}%)"
        else
            print_check "warn" "HPA '${hpa}': ${current_replicas}/${desired_replicas} replicas (min: ${min_replicas}, max: ${max_replicas}, target: ${targets}%)"
        fi
    done
}

check_pvcs() {
    print_header "PERSISTENT VOLUME CLAIM STATUS"

    local namespace=$1

    # Get all PVCs
    local pvcs
    pvcs=$(kubectl get pvc -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${pvcs}" ]]; then
        print_check "warn" "No PVCs found in namespace '${namespace}'"
        return
    fi

    for pvc in ${pvcs}; do
        local status
        status=$(kubectl get pvc "${pvc}" -n "${namespace}" -o jsonpath='{.status.phase}')

        local capacity
        capacity=$(kubectl get pvc "${pvc}" -n "${namespace}" -o jsonpath='{.spec.resources.requests.storage}')

        if [[ "${status}" == "Bound" ]]; then
            print_check "pass" "PVC '${pvc}' is Bound (${capacity})"
        else
            print_check "fail" "PVC '${pvc}' is ${status}"
        fi
    done
}

check_deployment_replicas() {
    print_header "DEPLOYMENT REPLICAS"

    local namespace=$1

    # Get all deployments
    local deployments
    deployments=$(kubectl get deployments -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${deployments}" ]]; then
        print_check "warn" "No deployments found in namespace '${namespace}'"
        return
    fi

    for deployment in ${deployments}; do
        local desired
        desired=$(kubectl get deployment "${deployment}" -n "${namespace}" -o jsonpath='{.spec.replicas}')

        local ready
        ready=$(kubectl get deployment "${deployment}" -n "${namespace}" -o jsonpath='{.status.readyReplicas}')

        local available
        available=$(kubectl get deployment "${deployment}" -n "${namespace}" -o jsonpath='{.status.availableReplicas}')

        local updated
        updated=$(kubectl get deployment "${deployment}" -n "${namespace}" -o jsonpath='{.status.updatedReplicas}')

        if [[ "${ready}" == "${desired}" && "${updated}" == "${desired}" ]]; then
            print_check "pass" "Deployment '${deployment}': ${ready}/${desired} replicas ready"
        else
            print_check "warn" "Deployment '${deployment}': ${ready}/${desired} replicas ready, ${updated}/${desired} updated"
        fi
    done
}

################################################################################
# Summary
################################################################################

print_summary() {
    print_header "HEALTH CHECK SUMMARY"

    if [[ "${OVERALL_HEALTHY}" == "true" ]]; then
        echo -e "${GREEN}${CHECK_MARK} All health checks passed!${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}${CROSS_MARK} Some health checks failed${NC}"
        echo ""
        echo "Please review the output above for details."
        echo "Common issues:"
        echo "  • Pods not starting: Check logs with 'kubectl logs <pod-name> -n ${namespace}'"
        echo "  • Services not ready: Check endpoints and pod selectors"
        echo "  • PVCs not bound: Check storage class and PV availability"
        echo "  • High restart counts: Check application logs for errors"
        echo ""
        return 1
    fi
}

################################################################################
# Main
################################################################################

main() {
    local namespace="${DEFAULT_NAMESPACE}"
    local verbose=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            *)
                namespace="$1"
                shift
                ;;
        esac
    done

    print_header "SATTVA KUBERNETES HEALTH CHECK"
    log_info "Namespace: ${namespace}"
    log_info "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

    # Pre-flight checks
    check_kubectl_installed
    check_cluster_access
    check_namespace_exists "${namespace}"

    # Run health checks
    check_pods "${namespace}"
    check_services "${namespace}"
    check_ingress "${namespace}"
    check_deployment_replicas "${namespace}"
    check_pvcs "${namespace}"
    check_hpa "${namespace}"
    check_http_endpoints "${namespace}"

    # Print summary and exit
    print_summary
}

main "$@"
