#!/bin/bash
################################################################################
# Kubernetes Preflight Check Script
# Performs pre-deployment validation checks
#
# Usage: ./scripts/k8s-preflight.sh [namespace]
#
# Arguments:
#   namespace    - Kubernetes namespace (default: sattva)
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
DEFAULT_NAMESPACE="sattva"
CHART_NAME="${CHART_NAME:-sattva}"

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

# Track check results
CRITICAL_FAILURES=0
WARNINGS=0
TOTAL_CHECKS=0

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
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
    ((TOTAL_CHECKS++))

    case "${status}" in
        pass)
            echo -e " ${GREEN}${CHECK_MARK}${NC} ${message}"
            ;;
        fail)
            echo -e " ${RED}${CROSS_MARK}${NC} ${message}"
            ((CRITICAL_FAILURES++))
            ;;
        warn)
            echo -e " ${YELLOW}${WARNING_MARK}${NC} ${message}"
            ((WARNINGS++))
            ;;
    esac
}

################################################################################
# Usage
################################################################################

usage() {
    cat << EOF
Usage: $(basename "$0") [namespace]

Performs pre-deployment validation checks for Kubernetes deployment.

Arguments:
  namespace    Kubernetes namespace (default: ${DEFAULT_NAMESPACE})

Options:
  -h, --help    Show this help message
  -f, --fix     Attempt to automatically fix issues (create namespace, etc.)
  --skip-helm-lint Skip Helm lint check (faster)

Checks performed:
  • kubectl installation and configuration
  • Helm installation
  • kubectl context validation
  • Helm repository availability
  • Cluster resource availability (nodes, CPU, memory)
  • Storage class availability
  • Namespace existence
  • Secret validation
  • Helm chart linting
  • Helm template rendering
  • Conflicting deployment detection

Exit codes:
  0 - All checks passed
  1 - Critical failures found
  2 - Error running checks

Examples:
  $(basename "$0")                    # Check default namespace
  $(basename "$0") sattva-prod        # Check production namespace
  $(basename "$0") sattva -f          # Auto-fix issues
  $(basename "$0") sattva --skip-helm-lint  # Skip lint check

EOF
    exit 0
}

################################################################################
# Check Functions
################################################################################

check_kubectl() {
    print_header "KUBECTL CHECKS"

    # Check if kubectl is installed
    if command -v kubectl &> /dev/null; then
        local version
        version=$(kubectl version --client --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
        print_check "pass" "kubectl is installed (${version})"
    else
        print_check "fail" "kubectl is not installed"
        log_info "Install kubectl: https://kubernetes.io/docs/tasks/tools/"
        return 1
    fi

    # Check cluster access
    if kubectl cluster-info &> /dev/null; then
        local cluster
        cluster=$(kubectl config current-context 2>/dev/null)
        print_check "pass" "Cluster access verified (context: ${cluster})"
    else
        print_check "fail" "Cannot access Kubernetes cluster"
        log_info "Check your kubeconfig file"
        return 1
    fi

    # Check context (warn if prod)
    local current_context
    current_context=$(kubectl config current-context 2>/dev/null || echo "unknown")

    if [[ "${current_context}" =~ (prod|production|live) ]]; then
        print_check "warn" "You are connected to a PRODUCTION cluster: ${current_context}"
    else
        print_check "pass" "kubectl context: ${current_context}"
    fi

    return 0
}

check_helm() {
    print_header "HELM CHECKS"

    # Check if Helm is installed
    if command -v helm &> /dev/null; then
        local version
        version=$(helm version --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+')
        print_check "pass" "Helm is installed (${version})"
    else
        print_check "fail" "Helm is not installed"
        log_info "Install Helm: https://helm.sh/docs/intro/install/"
        return 1
    fi

    # Check required Helm repos
    local required_repos=("bitnami")
    local missing_repos=()

    for repo in "${required_repos[@]}"; do
        if helm repo list | grep -q "^${repo}"; then
            print_check "pass" "Helm repository '${repo}' is available"
        else
            print_check "fail" "Helm repository '${repo}' is not configured"
            missing_repos+=("${repo}")
        fi
    done

    if [[ ${#missing_repos[@]} -gt 0 ]]; then
        log_info "Add missing repos: helm repo add ${missing_repos[0]} https://charts.bitnami.com/bitnami"
        return 1
    fi

    return 0
}

check_cluster_resources() {
    print_header "CLUSTER RESOURCE CHECKS"

    # Check nodes
    local nodes
    nodes=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)

    if [[ ${nodes} -gt 0 ]]; then
        print_check "pass" "Cluster has ${nodes} node(s)"
    else
        print_check "fail" "No nodes found in cluster"
        return 1
    fi

    # Check ready nodes
    local ready_nodes
    ready_nodes=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo "0")

    if [[ ${ready_nodes} -eq ${nodes} ]]; then
        print_check "pass" "All ${ready_nodes} node(s) are Ready"
    else
        print_check "warn" "${ready_nodes}/${nodes} node(s) are Ready"
    fi

    # Check CPU resources
    local total_cpu
    total_cpu=$(kubectl get nodes -o jsonpath='{.items[*].status.capacity.cpu}' 2>/dev/null | tr ' ' '+' | bc || echo "0")

    local allocatable_cpu
    allocatable_cpu=$(kubectl get nodes -o jsonpath='{.items[*].status.allocatable.cpu}' 2>/dev/null | tr ' ' '+' | bc || echo "0")

    if [[ ${total_cpu} -gt 0 ]]; then
        print_check "pass" "Total CPU: ${total_cpu} cores, Allocatable: ${allocatable_cpu} cores"
    fi

    # Check memory resources
    local total_memory
    total_memory=$(kubectl get nodes -o jsonpath='{.items[*].status.capacity.memory}' 2>/dev/null | head -1)

    local allocatable_memory
    allocatable_memory=$(kubectl get nodes -o jsonpath='{.items[*].status.allocatable.memory}' 2>/dev/null | head -1)

    if [[ -n "${total_memory}" ]]; then
        print_check "pass" "Total Memory: ${total_memory}, Allocatable: ${allocatable_memory}"
    fi

    return 0
}

check_storage_classes() {
    print_header "STORAGE CLASS CHECKS"

    # Check for storage classes
    local storage_classes
    storage_classes=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)

    if [[ ${storage_classes} -gt 0 ]]; then
        print_check "pass" "Found ${storage_classes} storage class(es)"

        # Check for default storage class
        local default_sc
        default_sc=$(kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null)

        if [[ -n "${default_sc}" ]]; then
            print_check "pass" "Default storage class: ${default_sc}"
        else
            print_check "warn" "No default storage class found"
        fi

        # List all storage classes
        kubectl get storageclass -o custom-columns=NAME:.metadata.name,PROVISIONER:.provisioner,DEFAULT:.metadata.annotations.storageclass\.kubernetes\.io/is-default-class 2>/dev/null | while IFS= read -r line; do
            echo "   └─ ${line}"
        done
    else
        print_check "fail" "No storage classes found"
        log_warning "PVCs cannot be created without a storage class"
        return 1
    fi

    return 0
}

check_namespace() {
    print_header "NAMESPACE CHECKS"

    local namespace=$1
    local auto_fix=$2

    # Check if namespace exists
    if kubectl get namespace "${namespace}" &> /dev/null; then
        print_check "pass" "Namespace '${namespace}' exists"
    else
        print_check "fail" "Namespace '${namespace}' does not exist"

        if [[ "${auto_fix}" == "true" ]]; then
            log_info "Creating namespace '${namespace}'..."
            if kubectl create namespace "${namespace}" &> /dev/null; then
                print_check "pass" "Namespace '${namespace}' created"
            else
                print_check "fail" "Failed to create namespace '${namespace}'"
                return 1
            fi
        else
            log_info "Create with: kubectl create namespace ${namespace}"
            return 1
        fi
    fi

    return 0
}

check_secrets() {
    print_header "SECRET CHECKS"

    local namespace=$1

    # Define required secrets (adjust based on your application)
    local required_secrets=()

    # Check for PostgreSQL secrets
    if kubectl get secret -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' | grep -q "postgresql"; then
        print_check "pass" "PostgreSQL secret found"
    else
        print_check "warn" "PostgreSQL secret not found (will use default)"
    fi

    # Check for Redis secrets
    if kubectl get secret -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' | grep -q "redis"; then
        print_check "pass" "Redis secret found"
    else
        print_check "warn" "Redis secret not found (will use default)"
    fi

    # Check for application secrets
    if kubectl get secret -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' | grep -q "sattva\|app"; then
        print_check "pass" "Application secrets found"
    else
        print_check "warn" "No application secrets found (check if this is expected)"
    fi

    return 0
}

check_helm_chart() {
    print_header "HELM CHART CHECKS"

    local chart_dir="${PROJECT_ROOT}/helm/${CHART_NAME}"
    local skip_lint=$1

    # Check if chart directory exists
    if [[ -d "${chart_dir}" ]]; then
        print_check "pass" "Chart directory exists: ${chart_dir}"
    else
        print_check "fail" "Chart directory not found: ${chart_dir}"
        return 1
    fi

    # Check Chart.yaml
    if [[ -f "${chart_dir}/Chart.yaml" ]]; then
        print_check "pass" "Chart.yaml found"
    else
        print_check "fail" "Chart.yaml not found"
        return 1
    fi

    # Check values files
    if [[ -f "${chart_dir}/values.yaml" ]]; then
        print_check "pass" "values.yaml found"
    else
        print_check "fail" "values.yaml not found"
        return 1
    fi

    if [[ -f "${chart_dir}/values-dev.yaml" ]]; then
        print_check "pass" "values-dev.yaml found"
    else
        print_check "warn" "values-dev.yaml not found (may be required for dev deployment)"
    fi

    if [[ -f "${chart_dir}/values-staging.yaml" ]]; then
        print_check "pass" "values-staging.yaml found"
    else
        print_check "warn" "values-staging.yaml not found (may be required for staging deployment)"
    fi

    if [[ -f "${chart_dir}/values-prod.yaml" ]]; then
        print_check "pass" "values-prod.yaml found"
    else
        print_check "warn" "values-prod.yaml not found (may be required for production deployment)"
    fi

    # Check templates directory
    if [[ -d "${chart_dir}/templates" ]]; then
        local template_count
        template_count=$(find "${chart_dir}/templates" -type f | wc -l)
        print_check "pass" "templates directory exists with ${template_count} file(s)"
    else
        print_check "fail" "templates directory not found"
        return 1
    fi

    # Run helm lint
    if [[ "${skip_lint}" != "true" ]]; then
        log_info "Running helm lint..."
        if helm lint "${chart_dir}" &> /dev/null; then
            print_check "pass" "Helm chart lint passed"
        else
            print_check "fail" "Helm chart lint failed"
            log_info "Run 'helm lint ${chart_dir}' for details"
            return 1
        fi
    else
        print_check "warn" "Helm lint skipped (--skip-helm-lint flag)"
    fi

    # Run helm template --debug
    log_info "Running helm template --debug..."
    if helm template "${CHART_NAME}" "${chart_dir}" --debug &> /dev/null; then
        print_check "pass" "Helm template rendering successful"
    else
        print_check "fail" "Helm template rendering failed"
        log_info "Run 'helm template ${CHART_NAME} ${chart_dir} --debug' for details"
        return 1
    fi

    return 0
}

check_conflicts() {
    print_header "CONFLICT CHECKS"

    local namespace=$1

    # Check for existing deployments with the same name
    local release_name="${RELEASE_NAME:-sattva}"

    if helm list -n "${namespace}" | grep -q "^${release_name}"; then
        print_check "warn" "Helm release '${release_name}' already exists (upgrade will be performed)"
    else
        print_check "pass" "No conflicting Helm release found"
    fi

    # Check for resource conflicts
    local deployments
    deployments=$(kubectl get deployments -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "${deployments}" ]]; then
        local deployment_count
        deployment_count=$(echo "${deployments}" | wc -w)
        print_check "pass" "Found ${deployment_count} existing deployment(s) in namespace '${namespace}'"
    fi

    return 0
}

################################################################################
# Summary
################################################################################

print_summary() {
    print_header "PREFLIGHT CHECK SUMMARY"

    echo "Total checks: ${TOTAL_CHECKS}"
    echo -e "  ${GREEN}Passed:${NC} $((TOTAL_CHECKS - CRITICAL_FAILURES - WARNINGS))"
    echo -e "  ${YELLOW}Warnings:${NC} ${WARNINGS}"
    echo -e "  ${RED}Critical failures:${NC} ${CRITICAL_FAILURES}"
    echo ""

    if [[ ${CRITICAL_FAILURES} -eq 0 ]]; then
        echo -e "${GREEN}${CHECK_MARK} All critical checks passed! Ready to deploy.${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}${CROSS_MARK} Critical failures found. Please fix before deploying.${NC}"
        echo ""
        echo "Recommendations:"
        echo "  • Review failed checks above"
        echo "  • Run with -f flag to auto-fix some issues"
        echo "  • Check documentation for manual fixes"
        echo ""
        return 1
    fi
}

################################################################################
# Main
################################################################################

main() {
    local namespace="${DEFAULT_NAMESPACE}"
    local auto_fix="false"
    local skip_helm_lint="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -f|--fix)
                auto_fix="true"
                shift
                ;;
            --skip-helm-lint)
                skip_helm_lint="true"
                shift
                ;;
            *)
                namespace="$1"
                shift
                ;;
        esac
    done

    print_header "KUBERNETES PREFLIGHT CHECKS"
    log_info "Namespace: ${namespace}"
    log_info "Auto-fix: ${auto_fix}"
    log_info "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

    # Run all checks
    check_kubectl || true
    check_helm || true
    check_cluster_resources || true
    check_storage_classes || true
    check_namespace "${namespace}" "${auto_fix}" || true
    check_secrets "${namespace}" || true
    check_helm_chart "${skip_helm_lint}" || true
    check_conflicts "${namespace}" || true

    # Print summary and exit
    print_summary
}

main "$@"
