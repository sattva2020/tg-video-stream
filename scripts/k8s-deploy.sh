#!/bin/bash
################################################################################
# Kubernetes Deployment Script
# Deploys Sattva application to Kubernetes using Helm
#
# Usage: ./scripts/k8s-deploy.sh [namespace] [environment]
#
# Arguments:
#   namespace    - Kubernetes namespace (default: sattva)
#   environment  - Environment: dev, staging, or prod (default: dev)
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
DEFAULT_NAMESPACE="sattva"
DEFAULT_ENVIRONMENT="dev"
CHART_NAME="${CHART_NAME:-sattva}"
RELEASE_NAME="${RELEASE_NAME:-sattva}"
HELM_REPOS_TIMEOUT="${HELM_REPOS_TIMEOUT:-300}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

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

################################################################################
# Usage
################################################################################

usage() {
    cat << EOF
Usage: $(basename "$0") [namespace] [environment]

Deploys Sattva application to Kubernetes using Helm.

Arguments:
  namespace    Kubernetes namespace (default: ${DEFAULT_NAMESPACE})
  environment  Environment: dev, staging, or prod (default: ${DEFAULT_ENVIRONMENT})

Options:
  -h, --help    Show this help message

Environment Variables:
  RELEASE_NAME  Helm release name (default: sattva)
  CHART_NAME    Chart name (default: sattva)

Examples:
  $(basename "$0")                           # Deploy with defaults
  $(basename "$0") sattva dev                # Deploy to dev environment
  $(basename "$0") sattva-production prod    # Deploy to production
  RELEASE_NAME=myapp $(basename "$0") sattva staging  # Custom release name

EOF
    exit 0
}

################################################################################
# Helper Functions
################################################################################

check_helm_installed() {
    log_info "Checking if Helm is installed..."

    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install Helm 3.x"
        log_info "Visit: https://helm.sh/docs/intro/install/"
        exit 1
    fi

    local helm_version
    helm_version=$(helm version --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
    log_success "Helm is installed: ${helm_version}"
}

check_kubectl_installed() {
    log_info "Checking if kubectl is installed..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl"
        log_info "Visit: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    local kubectl_version
    kubectl_version=$(kubectl version --client --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
    log_success "kubectl is installed: ${kubectl_version}"
}

check_cluster_access() {
    log_info "Checking Kubernetes cluster access..."

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster. Please configure kubeconfig"
        exit 1
    fi

    local cluster_context
    cluster_context=$(kubectl config current-context 2>/dev/null)
    log_success "Connected to cluster: ${cluster_context}"
}

validate_environment() {
    local env=$1

    case "${env}" in
        dev|staging|prod)
            log_success "Valid environment: ${env}"
            ;;
        *)
            log_error "Invalid environment: ${env}. Must be one of: dev, staging, prod"
            exit 1
            ;;
    esac
}

add_helm_repositories() {
    log_info "Adding required Helm repositories..."

    local repos=(
        "bitnami,https://charts.bitnami.com/bitnami"
    )

    for repo in "${repos[@]}"; do
        IFS=',' read -r repo_name repo_url <<< "${repo}"

        if helm repo list | grep -q "^${repo_name}"; then
            log_info "Repository '${repo_name}' already exists. Updating..."
            helm repo update "${repo_name}" > /dev/null 2>&1
        else
            log_info "Adding repository: ${repo_name}"
            helm repo add "${repo_name}" "${repo_url}" > /dev/null 2>&1
        fi
    done

    log_success "Helm repositories updated"
}

update_helm_dependencies() {
    log_info "Updating Helm chart dependencies..."

    local chart_dir="${PROJECT_ROOT}/helm/${CHART_NAME}"

    if [[ ! -d "${chart_dir}" ]]; then
        log_error "Chart directory not found: ${chart_dir}"
        exit 1
    fi

    if [[ -f "${chart_dir}/Chart.lock" ]]; then
        log_info "Removing existing Chart.lock..."
        rm -f "${chart_dir}/Chart.lock"
    fi

    pushd "${chart_dir}" > /dev/null
    if helm dependency update > /dev/null 2>&1; then
        log_success "Helm dependencies updated"
    else
        log_warning "No dependencies found or dependency update failed"
    fi
    popd > /dev/null
}

check_release_exists() {
    local namespace=$1
    local release_name=$2

    if helm list -n "${namespace}" | grep -q "^${release_name}"; then
        return 0  # Release exists
    else
        return 1  # Release does not exist
    fi
}

install_release() {
    local namespace=$1
    local environment=$2
    local chart_dir="${PROJECT_ROOT}/helm/${CHART_NAME}"
    local values_file="${chart_dir}/values-${environment}.yaml"

    log_info "Installing Helm release '${RELEASE_NAME}' in namespace '${namespace}'..."

    local helm_args=(
        install
        "${RELEASE_NAME}"
        "${chart_dir}"
        --namespace "${namespace}"
        --create-namespace
        --wait
        --timeout 10m
        --values "${values_file}"
        --set "global.environment=${environment}"
    )

    if [[ "${environment}" == "prod" ]]; then
        helm_args+=(--set "global.replicaCount=3")
    fi

    if helm "${helm_args[@]}"; then
        log_success "Helm release '${RELEASE_NAME}' installed successfully"
        return 0
    else
        log_error "Failed to install Helm release '${RELEASE_NAME}'"
        return 1
    fi
}

upgrade_release() {
    local namespace=$1
    local environment=$2
    local chart_dir="${PROJECT_ROOT}/helm/${CHART_NAME}"
    local values_file="${chart_dir}/values-${environment}.yaml"

    log_info "Upgrading Helm release '${RELEASE_NAME}' in namespace '${namespace}'..."

    local helm_args=(
        upgrade
        "${RELEASE_NAME}"
        "${chart_dir}"
        --namespace "${namespace}"
        --wait
        --timeout 10m
        --values "${values_file}"
        --set "global.environment=${environment}"
        --install
    )

    if [[ "${environment}" == "prod" ]]; then
        helm_args+=(--set "global.replicaCount=3")
    fi

    if helm "${helm_args[@]}"; then
        log_success "Helm release '${RELEASE_NAME}' upgraded successfully"
        return 0
    else
        log_error "Failed to upgrade Helm release '${RELEASE_NAME}'"
        return 1
    fi
}

wait_for_rollout() {
    local namespace=$1

    log_info "Waiting for deployments to rollout..."

    local deployments
    deployments=$(kubectl get deployments -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${deployments}" ]]; then
        log_warning "No deployments found in namespace '${namespace}'"
        return 0
    fi

    for deployment in ${deployments}; do
        log_info "Waiting for deployment '${deployment}' to be ready..."

        if kubectl rollout status deployment/"${deployment}" -n "${namespace}" --timeout=5m; then
            log_success "Deployment '${deployment}' is ready"
        else
            log_error "Deployment '${deployment}' failed to become ready"
            return 1
        fi
    done

    log_success "All deployments are ready"
}

verify_deployment_health() {
    local namespace=$1

    log_info "Verifying deployment health..."

    # Check pod status
    local pods
    pods=$(kubectl get pods -n "${namespace}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${pods}" ]]; then
        log_error "No pods found in namespace '${namespace}'"
        return 1
    fi

    local not_ready=0
    for pod in ${pods}; do
        local pod_status
        pod_status=$(kubectl get pod "${pod}" -n "${namespace}" -o jsonpath='{.status.phase}')

        if [[ "${pod_status}" != "Running" && "${pod_status}" != "Succeeded" ]]; then
            log_error "Pod '${pod}' is not ready (status: ${pod_status})"
            ((not_ready++))
        else
            log_success "Pod '${pod}' is ready"
        fi
    done

    if [[ ${not_ready} -gt 0 ]]; then
        log_error "${not_ready} pod(s) are not ready"
        return 1
    fi

    log_success "All pods are healthy"
    return 0
}

################################################################################
# Main
################################################################################

main() {
    local namespace="${DEFAULT_NAMESPACE}"
    local environment="${DEFAULT_ENVIRONMENT}"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            *)
                if [[ -z "${namespace_set:-}" ]]; then
                    namespace="$1"
                    namespace_set=1
                elif [[ -z "${environment_set:-}" ]]; then
                    environment="$1"
                    environment_set=1
                else
                    log_error "Unknown argument: $1"
                    usage
                fi
                ;;
        esac
        shift
    done

    log_info "Starting deployment..."
    log_info "Namespace: ${namespace}"
    log_info "Environment: ${environment}"
    log_info "Release Name: ${RELEASE_NAME}"

    # Pre-flight checks
    check_helm_installed
    check_kubectl_installed
    check_cluster_access
    validate_environment "${environment}"

    # Setup Helm
    add_helm_repositories
    update_helm_dependencies

    # Deploy
    if check_release_exists "${namespace}" "${RELEASE_NAME}"; then
        log_info "Release '${RELEASE_NAME}' already exists. Performing upgrade..."
        if ! upgrade_release "${namespace}" "${environment}"; then
            log_error "Upgrade failed"
            exit 1
        fi
    else
        log_info "Release '${RELEASE_NAME}' does not exist. Performing install..."
        if ! install_release "${namespace}" "${environment}"; then
            log_error "Installation failed"
            exit 1
        fi
    fi

    # Wait for rollout
    if ! wait_for_rollout "${namespace}"; then
        log_error "Rollout failed"
        exit 1
    fi

    # Verify health
    if ! verify_deployment_health "${namespace}"; then
        log_warning "Health verification found issues, but deployment completed"
        log_info "Run './scripts/k8s-health-check.sh ${namespace}' for detailed status"
    fi

    log_success "Deployment completed successfully!"
    log_info "Access the application using: kubectl get ingress -n ${namespace}"
}

main "$@"
