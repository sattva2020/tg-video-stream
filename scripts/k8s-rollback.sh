#!/bin/bash
################################################################################
# Kubernetes Rollback Script
# Rolls back a Helm release to a previous revision
#
# Usage: ./scripts/k8s-rollback.sh [namespace] [release-name]
#
# Arguments:
#   namespace    - Kubernetes namespace (default: sattva)
#   release-name - Helm release name (default: sattva)
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
DEFAULT_NAMESPACE="sattva"
DEFAULT_RELEASE_NAME="sattva"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
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
Usage: $(basename "$0") [namespace] [release-name]

Rolls back a Helm release to a previous revision.

Arguments:
  namespace    Kubernetes namespace (default: ${DEFAULT_NAMESPACE})
  release-name Helm release name (default: ${DEFAULT_RELEASE_NAME})

Options:
  -h, --help    Show this help message
  -y, --yes     Skip confirmation prompt (use with caution)

Examples:
  $(basename "$0")                              # Rollback with defaults
  $(basename "$0") sattva myapp                 # Rollback specific release
  $(basename "$0") sattva-production sattva -y  # Rollback without confirmation

Workflow:
  1. Script displays recent release history
  2. User selects which revision to rollback to
  3. Script performs safety confirmation
  4. Rollback is executed
  5. Rollout status is monitored
  6. Health verification is performed

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
        exit 1
    fi

    log_success "Helm is installed"
}

check_kubectl_installed() {
    log_info "Checking if kubectl is installed..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl"
        exit 1
    fi

    log_success "kubectl is installed"
}

check_cluster_access() {
    log_info "Checking Kubernetes cluster access..."

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster. Please configure kubeconfig"
        exit 1
    fi

    log_success "Connected to cluster"
}

check_release_exists() {
    local namespace=$1
    local release_name=$2

    if ! helm list -n "${namespace}" | grep -q "^${release_name}"; then
        log_error "Release '${release_name}' not found in namespace '${namespace}'"
        log_info "Available releases:"
        helm list -n "${namespace}"
        exit 1
    fi

    log_success "Release '${release_name}' found"
}

display_release_history() {
    local namespace=$1
    local release_name=$2

    log_info "Fetching release history for '${release_name}'..."

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Release History: ${release_name}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    helm history "${release_name}" -n "${namespace}" -o table | while IFS= read -r line; do
        if [[ "${line}" =~ ^REVISION ]]; then
            echo -e "${CYAN}${line}${NC}"
        else
            local revision status updated description
            revision=$(echo "${line}" | awk '{print $1}')
            status=$(echo "${line}" | awk '{print $3}')

            case "${status}" in
                deployed)
                    echo -e "${GREEN}${line}${NC}"
                    ;;
                superseded)
                    echo -e "${YELLOW}${line}${NC}"
                    ;;
                failed)
                    echo -e "${RED}${line}${NC}"
                    ;;
                *)
                    echo "${line}"
                    ;;
            esac
        fi
    done

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

select_revision() {
    local namespace=$1
    local release_name=$2

    log_info "Available revisions:"
    echo ""

    local revisions
    revisions=$(helm history "${release_name}" -n "${namespace}" -o json | \
                jq -r '.[] | select(.status != "pending-upgrade" and .status != "pending-install" and .status != "pending-rollback") | "\(.revision) | \(.status) | \(.updated) | \(.description)"' | \
                tail -10)

    if [[ -z "${revisions}" ]]; then
        log_error "No valid revisions found for rollback"
        exit 1
    fi

    echo "${revisions}" | while IFS='|' read -r revision status updated description; do
        local clean_desc
        clean_desc=$(echo "${description}" | xargs)
        case "${status}" in
            deployed)
                echo -e "  ${GREEN}${revision}${NC} - ${status} - ${clean_desc}"
                ;;
            superseded)
                echo -e "  ${YELLOW}${revision}${NC} - ${status} - ${clean_desc}"
                ;;
            *)
                echo "  ${revision} - ${status} - ${clean_desc}"
                ;;
        esac
    done
    echo ""

    read -p "Enter revision number to rollback to: " selected_revision

    # Validate revision exists
    if ! helm history "${release_name}" -n "${namespace}" | grep -q "^${selected_revision} "; then
        log_error "Invalid revision number: ${selected_revision}"
        exit 1
    fi

    # Get current revision
    local current_revision
    current_revision=$(helm history "${release_name}" -n "${namespace}" -o json | \
                      jq -r '.[] | select(.status == "deployed") | .revision')

    if [[ "${selected_revision}" == "${current_revision}" ]]; then
        log_warning "Revision ${selected_revision} is the currently deployed version"
        read -p "Continue anyway? (y/N): " confirm
        if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
            log_info "Rollback cancelled"
            exit 0
        fi
    fi

    echo "${selected_revision}"
}

confirm_rollback() {
    local namespace=$1
    local release_name=$2
    local revision=$3
    local skip_confirm=$4

    if [[ "${skip_confirm}" == "true" ]]; then
        log_warning "Skipping confirmation (auto-confirmed with -y flag)"
        return 0
    fi

    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}⚠️  ROLLBACK CONFIRMATION REQUIRED${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Release:${NC}     ${release_name}"
    echo -e "  ${CYAN}Namespace:${NC}    ${namespace}"
    echo -e "  ${CYAN}Rollback to:${NC}  Revision ${revision}"
    echo ""
    echo -e "${RED}This action will:${NC}"
    echo -e "  • Roll back the deployment to revision ${revision}"
    echo -e "  • Update all pods, services, and configurations"
    echo -e "  • May cause brief service interruption"
    echo ""
    echo -e "${YELLOW}Type 'ROLLBACK' to confirm or 'cancel' to abort:${NC} "

    read -r confirmation

    if [[ "${confirmation}" != "ROLLBACK" ]]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi

    log_success "Rollback confirmed"
}

perform_rollback() {
    local namespace=$1
    local release_name=$2
    local revision=$3

    log_info "Performing rollback to revision ${revision}..."

    if helm rollback "${release_name}" "${revision}" -n "${namespace}" --wait --timeout 10m; then
        log_success "Rollback completed successfully"
        return 0
    else
        log_error "Rollback failed"
        return 1
    fi
}

wait_for_rollout() {
    local namespace=$1
    local release_name=$2

    log_info "Waiting for rollout to complete..."

    # Get all deployments managed by this release
    local deployments
    deployments=$(kubectl get deployments -n "${namespace}" \
                  -o jsonpath='{.items[?(@.metadata.labels.app\.kubernetes\.io/instance=="'${release_name}'")].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${deployments}" ]]; then
        log_warning "No deployments found for release '${release_name}'"
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

    log_success "All deployments rolled back successfully"
}

verify_rollback() {
    local namespace=$1
    local release_name=$2
    local target_revision=$3

    log_info "Verifying rollback..."

    # Check current revision
    local current_revision
    current_revision=$(helm history "${release_name}" -n "${namespace}" -o json | \
                      jq -r '.[] | select(.status == "deployed") | .revision')

    if [[ "${current_revision}" == "${target_revision}" ]]; then
        log_success "Rollback verified: Release is now at revision ${current_revision}"
    else
        log_warning "Expected revision ${target_revision} but got ${current_revision}"
    fi

    # Check pod health
    local pods
    pods=$(kubectl get pods -n "${namespace}" \
           -o jsonpath='{.items[?(@.metadata.labels.app\.kubernetes\.io/instance=="'${release_name}'")].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "${pods}" ]]; then
        for pod in ${pods}; do
            local pod_status
            pod_status=$(kubectl get pod "${pod}" -n "${namespace}" -o jsonpath='{.status.phase}')

            if [[ "${pod_status}" != "Running" && "${pod_status}" != "Succeeded" ]]; then
                log_warning "Pod '${pod}' status: ${pod_status}"
            else
                log_success "Pod '${pod}' is healthy"
            fi
        done
    fi
}

display_rollback_summary() {
    local namespace=$1
    local release_name=$2
    local revision=$3

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ROLLBACK COMPLETED SUCCESSFULLY${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Release:${NC}       ${release_name}"
    echo -e "  ${CYAN}Namespace:${NC}      ${namespace}"
    echo -e "  ${CYAN}New Revision:${NC}   ${revision}"
    echo ""
    echo -e "Next steps:"
    echo -e "  • Verify application health: ${YELLOW}./scripts/k8s-health-check.sh ${namespace}${NC}"
    echo -e "  • View release history:     ${YELLOW}helm history ${release_name} -n ${namespace}${NC}"
    echo -e "  • Check logs:               ${YELLOW}kubectl logs -n ${namespace} -l app.kubernetes.io/instance=${release_name}${NC}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

################################################################################
# Main
################################################################################

main() {
    local namespace="${DEFAULT_NAMESPACE}"
    local release_name="${DEFAULT_RELEASE_NAME}"
    local skip_confirm="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -y|--yes)
                skip_confirm="true"
                shift
                ;;
            *)
                if [[ -z "${namespace_set:-}" ]]; then
                    namespace="$1"
                    namespace_set=1
                elif [[ -z "${release_set:-}" ]]; then
                    release_name="$1"
                    release_set=1
                else
                    log_error "Unknown argument: $1"
                    usage
                fi
                ;;
        esac
        shift
    done

    log_info "Starting rollback process..."
    log_info "Namespace: ${namespace}"
    log_info "Release Name: ${release_name}"

    # Pre-flight checks
    check_helm_installed
    check_kubectl_installed
    check_cluster_access
    check_release_exists "${namespace}" "${release_name}"

    # Display history and select revision
    display_release_history "${namespace}" "${release_name}"
    local selected_revision
    selected_revision=$(select_revision "${namespace}" "${release_name}")

    # Safety confirmation
    confirm_rollback "${namespace}" "${release_name}" "${selected_revision}" "${skip_confirm}"

    # Perform rollback
    if ! perform_rollback "${namespace}" "${release_name}" "${selected_revision}"; then
        log_error "Rollback failed"
        exit 1
    fi

    # Wait for rollout
    if ! wait_for_rollout "${namespace}" "${release_name}"; then
        log_warning "Rollback completed but some deployments may not be ready"
    fi

    # Verify rollback
    verify_rollback "${namespace}" "${release_name}" "${selected_revision}"

    # Display summary
    display_rollback_summary "${namespace}" "${release_name}" "${selected_revision}"
}

main "$@"
