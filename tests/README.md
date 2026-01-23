# Kubernetes Deployment Tests

Comprehensive test suite for Sattva Streamer Kubernetes deployment.

## Prerequisites

- Kubernetes cluster (minikube, kind, or cloud K8s)
- kubectl configured and pointing to test cluster
- Helm 3.x installed
- helm unittest plugin installed (for unit tests)
- Access to container registry (or images available locally)

### Install Tools

```bash
# Install helm unittest plugin
helm plugin install https://github.com/quintush/helm-unittest

# Verify tools
kubectl version --client
helm version
helm unittest --help
```

## Test Structure

```
tests/
├── helm/
│   ├── unit_test.yaml          # Helm template unit tests
│   └── integration/
│       └── deployment_test.sh  # Integration tests (deploy to cluster)
├── e2e/
│   └── k8s-deployment-e2e.test.sh  # End-to-end deployment tests
├── autoscaling/
│   ├── hpa_verification_test.sh    # HPA scaling verification
│   └── load_test.sh                # Load generation for testing
└── disaster-recovery/
    └── backup_restore_test.sh      # Backup and restore tests
```

## Running Tests

### 1. Unit Tests (Helm Template Validation)

Test that Helm templates render correctly without deploying.

```bash
# Run all unit tests
cd helm/sattva-streamer
helm unittest .

# Run with verbose output
helm unittest . --verbose

# Run specific test suite
helm unittest . -file tests/unit_test.yaml
```

**Expected Output**: All tests should pass with green checkmarks.

**What it tests**:
- Deployments, StatefulSets render correctly
- Services configured properly
- HPA resources created when autoscaling enabled
- ConfigMaps and Secrets render
- Ingress configuration
- PodDisruptionBudgets
- ServiceMonitors

### 2. Integration Tests (Deploy to Test Cluster)

Deploy to a real Kubernetes cluster and verify resources.

```bash
# Run integration tests
cd tests/helm/integration
./deployment_test.sh

# Or from project root
./tests/helm/integration/deployment_test.sh [namespace]
```

**What it tests**:
- Helm chart installs successfully
- All pods become Ready
- All Services are created
- Services are reachable
- Health endpoints return 200 OK
- PVCs are Bound
- HPA resources exist
- Resources cleaned up after tests

**Prerequisites**:
- Test cluster running (minikube start, kind create cluster, etc.)
- kubectl configured to point to test cluster
- Sufficient cluster resources

### 3. E2E Tests (Full Stack Deployment)

Deploy entire application and verify functionality.

```bash
# Run E2E tests
cd tests/e2e
./k8s-deployment-e2e.test.sh [namespace]

# Or from project root
./tests/e2e/k8s-deployment-e2e.test.sh sattva
```

**What it tests**:
1. Full stack deployment with scripts/k8s-deploy.sh
2. All services become healthy
3. Frontend loads: `curl http://frontend/`
4. Backend API healthy: `curl http://backend/api/health/ready`
5. Transcoder healthy: `curl http://transcoder/health`
6. Streamer connectivity (check logs for errors)
7. Ingress routing works
8. TLS certificates valid
9. Health check script passes: `./scripts/k8s-health-check.sh`
10. Cleanup

**Duration**: ~10-15 minutes

### 4. Autoscaling Verification Tests

Test HPA functionality by generating load.

```bash
# Run autoscaling verification
cd tests/autoscaling
./hpa_verification_test.sh [namespace]

# Or from project root
./tests/autoscaling/hpa_verification_test.sh sattva
```

**What it tests**:
- HPA resources exist
- Check HPA status (replicas, metrics)
- Generate load on services
- Monitor HPA scale-up (replicas increase)
- Verify new pods become Ready
- Stop load
- Monitor HPA scale-down (replicas decrease)
- Test each service (backend, frontend, transcoder)
- Log HPA behavior

**Duration**: ~5-10 minutes per service

**Load Generation**: Uses Apache Bench (ab) or k6 to generate CPU load.

### 5. Disaster Recovery Tests

Test backup and restore procedures.

```bash
# Run disaster recovery tests
cd tests/disaster-recovery
./backup_restore_test.sh [namespace]

# Or from project root
./tests/disaster-recovery/backup_restore_test.sh sattva
```

**What it tests**:
- Create backup of PostgreSQL
- Create backup of Redis
- Simulate data loss (delete data)
- Restore PostgreSQL from backup
- Restore Redis from backup
- Verify data integrity
- Test application still works after restore

**Duration**: ~10 minutes

**Safety**: Tests use test namespace, won't affect production data.

## Run All Tests

Master test script that runs all test suites in order.

```bash
cd tests
./run_all_tests.sh [namespace]
```

**Test Order**:
1. Unit tests (fast, no cluster needed)
2. Integration tests (requires cluster)
3. E2E tests (requires cluster, takes longest)
4. Autoscaling tests (requires cluster)
5. Disaster recovery tests (requires cluster)

**Total Duration**: ~30-45 minutes

**Output**: Generates test report with pass/fail status.

## Test Reports

After running tests, check the generated reports:

```bash
# View latest test results
cat tests/test-results/latest.txt

# View detailed logs
cat tests/logs/test-run-$(date +%Y%m%d-%H%M%S).log
```

## Troubleshooting

### Unit Tests Fail

```bash
# Check template syntax
helm template test helm/sattva-streamer/

# Lint the chart
cd helm/sattva-streamer
helm lint .
```

### Integration Tests Fail

```bash
# Check cluster status
kubectl get nodes
kubectl get pods -A

# Check specific pod logs
kubectl logs -n <namespace> <pod-name>

# Describe failing resource
kubectl describe -n <namespace> pod <pod-name>
```

### E2E Tests Fail

```bash
# Run health check manually
./scripts/k8s-health-check.sh <namespace>

# Check all services
kubectl get svc -n <namespace>
kubectl get pods -n <namespace>

# Check ingress
kubectl get ingress -n <namespace>
kubectl describe ingress -n <namespace>
```

### Autoscaling Tests Fail

```bash
# Check HPA status
kubectl get hpa -n <namespace>
kubectl describe hpa -n <namespace> <hpa-name>

# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io

# Verify metrics are being collected
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods
```

### Disaster Recovery Tests Fail

```bash
# Check backup storage
ls -la /backups/postgresql/
ls -la /backups/redis/

# Verify backup tools installed
which pg_dump
which redis-cli
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/k8s-tests.yml
name: Kubernetes Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Helm
        uses: azure/setup-helm@v3
      - name: Install helm unittest
        run: helm plugin install https://github.com/quintush/helm-unittest
      - name: Run unit tests
        run: cd helm/sattva-streamer && helm unittest .

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - name: Create kind cluster
        uses: helm/kind-action@v1
      - name: Run integration tests
        run: ./tests/helm/integration/deployment_test.sh
```

## Cleanup

Remove test resources:

```bash
# Delete test namespace
kubectl delete namespace sattva-test

# Or use Helm uninstall
helm uninstall sattva-test -n sattva-test

# Clean up test data
rm -rf tests/test-results/
rm -rf tests/logs/
```

## Best Practices

1. **Run tests before every deployment** - Catch issues early
2. **Test in staging first** - Never test directly in production
3. **Automate in CI/CD** - Run unit tests on every PR
4. **Monitor test duration** - Slow tests need optimization
5. **Keep tests isolated** - Each test should clean up after itself
6. **Use test-specific configs** - Don't use production credentials
7. **Document test failures** - Track and fix flaky tests

## Support

For issues with tests:
1. Check test logs: `tests/logs/`
2. Review troubleshooting section above
3. Check Helm chart: `cd helm/sattva-streamer && helm lint .`
4. Verify cluster: `kubectl cluster-info`
5. Open issue: https://github.com/sattva-streamer/sattva/issues
