# Kubernetes Deployment Guide for Sattva Streamer

This comprehensive guide covers the complete deployment process for Sattva Telegram Streamer on Kubernetes using Helm charts.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Cluster Requirements](#cluster-requirements)
- [Installation Steps](#installation-steps)
- [Configuration Options](#configuration-options)
- [Environment-Specific Settings](#environment-specific-settings)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Upgrade Procedures](#upgrade-procedures)
- [Uninstall Procedures](#uninstall-procedures)

---

## Prerequisites

Before deploying Sattva Streamer to Kubernetes, ensure you have the following tools installed and configured:

### Required Tools

#### 1. kubectl (Kubernetes Command-Line Tool)

**Installation:**

```bash
# Linux (AMD64)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS (using Homebrew)
brew install kubectl

# Windows (using Chocolatey)
choco install kubernetes-cli
```

**Verification:**

```bash
kubectl version --client
```

#### 2. Helm (Package Manager for Kubernetes)

**Installation:**

```bash
# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# macOS
brew install helm

# Windows
choco install kubernetes-helm
```

**Verification:**

```bash
helm version
```

#### 3. Cluster Access

Ensure you have:

- `~/.kube/config` file configured with cluster access
- Appropriate RBAC permissions to deploy resources
- Network access to the Kubernetes API server

**Verify cluster access:**

```bash
kubectl cluster-info
kubectl get nodes
```

### Recommended Additional Tools

```bash
# kubectx/kubens for context switching
git clone https://github.com/ahmetb/kubectx /opt/kubectx
sudo ln -s /opt/kubectx/kubectx /usr/local/bin/kubectx
sudo ln -s /opt/kubectx/kubens /usr/local/bin/kubens

# k9s for cluster monitoring
# Download from https://github.com/derailed/k9s/releases

# stern for log aggregation
# Download from https://github.com/stern/stern/releases
```

---

## Cluster Requirements

### Minimum Cluster Specifications

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **Nodes** | 3 | 5+ |
| **vCPUs** | 12 | 24+ |
| **Memory** | 24 GB | 48 GB+ |
| **Storage** | 50 GB | 200 GB+ |

### Node Requirements

Each node should meet these specifications:

- **Operating System**: Ubuntu 20.04+, CentOS 8+, or any Kubernetes-certified OS
- **Container Runtime**: containerd 1.6+ or Docker CE 20.10+
- **Network**: CNI plugin installed (Calico, Flannel, or Cilium)
- **Port Requirements**:
  - 80/443 (Ingress)
  - 30000-32767 (NodePort services, if used)
  - 6443 (Kubernetes API server)

### Storage Classes

Required storage classes:

```bash
# Check available storage classes
kubectl get storageclass

# Example expected output:
# NAME                 PROVISIONER           RECLAIM POLICY
# standard (default)   kubernetes.io/aws-ebs  Delete
# gp2                  kubernetes.io/aws-ebs  Delete
```

**Required storage capacities:**

- PostgreSQL: 10 GiB (expandable)
- Redis: 5 GiB (expandable)
- Streamer sessions: 1 GiB per streamer instance

### Resource Requirements by Service

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| **Backend** | 250m | 1000m | 256 MiB | 512 MiB |
| **Frontend** | 100m | 200m | 64 MiB | 128 MiB |
| **Streamer** | 200m | 500m | 128 MiB | 256 MiB |
| **Rust Transcoder** | 100m | 500m | 128 MiB | 512 MiB |
| **PostgreSQL** | 250m | 500m | 256 MiB | 512 MiB |
| **Redis** | 100m | 200m | 128 MiB | 256 MiB |

---

## Installation Steps

### Step 1: Install Tools (if not already installed)

```bash
# Verify kubectl
kubectl version --client

# Verify Helm
helm version

# Verify cluster access
kubectl cluster-info
kubectl get nodes
```

### Step 2: Configure kubectl Context

```bash
# List available contexts
kubectl config get-contexts

# Switch to the desired context
kubectl config use-context <your-cluster-name>

# Verify current context
kubectl config current-context

# Set default namespace for the deployment
kubectl create namespace sattva-prod
kubectl config set-context --current --namespace=sattva-prod
```

### Step 3: Prepare Secrets

Create Kubernetes secrets for sensitive configuration:

```bash
# Create namespace
kubectl create namespace sattva-prod

# Create JWT secret
kubectl create secret generic sattva-jwt-secret \
  --from-literal=JWT_SECRET='your-secure-jwt-secret-here' \
  --namespace=sattva-prod

# Create Google Drive API key secret
kubectl create secret generic sattva-google-credentials \
  --from-literal=GOOGLE_DRIVE_API_KEY='your-google-api-key' \
  --namespace=sattva-prod

# Create Telegram credentials secret
kubectl create secret generic sattva-telegram-credentials \
  --from-literal=API_ID='your-telegram-api-id' \
  --from-literal=API_HASH='your-telegram-api-hash' \
  --namespace=sattva-prod

# Create Alertmanager Telegram secret
kubectl create secret generic sattva-alertmanager-telegram \
  --from-literal=BOT_TOKEN='your-alertmanager-bot-token' \
  --from-literal=CHAT_ID='your-alertmanager-chat-id' \
  --namespace=sattva-prod

# Create AI provider API keys secret
kubectl create secret generic sattva-ai-keys \
  --from-literal=OPENAI_API_KEY='your-openai-key' \
  --from-literal=ANTHROPIC_API_KEY='your-anthropic-key' \
  --from-literal=OPENROUTER_API_KEY='your-openrouter-key' \
  --from-literal=DEEPSEEK_API_KEY='your-deepseek-key' \
  --from-literal=QWEN_API_KEY='your-qwen-key' \
  --from-literal=ZAI_API_KEY='your-zai-key' \
  --from-literal=GEMINI_API_KEY='your-gemini-key' \
  --namespace=sattva-prod

# Verify all secrets
kubectl get secrets --namespace=sattva-prod
```

### Step 4: Run Pre-flight Checks

Execute the pre-flight check script to verify cluster readiness:

```bash
# Navigate to project root
cd /path/to/sattva-streamer

# Make script executable
chmod +x scripts/k8s-preflight.sh

# Run pre-flight checks
./scripts/k8s-preflight.sh sattva prod
```

**Expected pre-flight checks:**

- [ ] Kubernetes cluster connectivity
- [ ] kubectl version compatibility
- [ ] Helm version compatibility
- [ ] Resource availability (CPU, memory, storage)
- [ ] Storage class availability
- [ ] Namespace creation capability
- [ ] Secret creation capability
- [ ] Network policies (if enabled)

**If any check fails:**

- Review the error message
- Fix the issue manually or follow the suggested remediation
- Re-run the pre-flight checks until all pass

### Step 5: Deploy the Application

Use the deployment script to install the Helm chart:

```bash
# Navigate to project root
cd /path/to/sattva-streamer

# Make script executable
chmod +x scripts/k8s-deploy.sh

# Deploy to production environment
./scripts/k8s-deploy.sh sattva prod

# Or deploy to staging
./scripts/k8s-deploy.sh sattva staging

# Or deploy to development
./scripts/k8s-deploy.sh sattva dev
```

**What the deployment script does:**

1. Validates the environment parameter
2. Sets up the appropriate values file (values-prod.yaml, values-staging.yaml, or values-dev.yaml)
3. Installs or upgrades the Helm release
4. Waits for pods to be ready
5. Displays deployment status

**Manual deployment (if script fails):**

```bash
# Add Helm chart repository (if applicable)
helm repo add sattva https://charts.sattva-streamer.top
helm repo update

# Install the chart
helm install sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --values helm/sattva-streamer/values.yaml \
  --values helm/sattva-streamer/values-prod.yaml \
  --timeout 15m \
  --wait

# Check deployment status
helm status sattva-prod --namespace sattva-prod
```

### Step 6: Verify Deployment

Run health checks to ensure all services are running:

```bash
# Run health check script
chmod +x scripts/k8s-health-check.sh
./scripts/k8s-health-check.sh sattva

# Manual verification
kubectl get pods --namespace=sattva-prod
kubectl get services --namespace=sattva-prod
kubectl get ingress --namespace=sattva-prod

# Check pod status in detail
kubectl describe pods --namespace=sattva-prod

# View logs for each service
kubectl logs -l app=backend --namespace=sattva-prod --tail=50
kubectl logs -l app=frontend --namespace=sattva-prod --tail=50
kubectl logs -l app=streamer --namespace=sattva-prod --tail=50
kubectl logs -l app=rust-transcoder --namespace=sattva-prod --tail=50

# Verify database connectivity
kubectl exec -it sattva-prod-postgresql-0 --namespace=sattva-prod -- psql -U postgres -d telegram_db -c "SELECT version();"

# Verify Redis connectivity
kubectl exec -it sattva-prod-redis-master-0 --namespace=sattva-prod -- redis-cli PING
```

**Expected deployment state:**

```
NAME                                 READY   STATUS    RESTARTS   AGE
sattva-prod-backend-7d9f7d8f-x9k2p   1/1     Running   0          2m
sattva-prod-frontend-6b8f9d5c-x4k8n   1/1     Running   0          2m
sattva-prod-streamer-0                1/1     Running   0          2m
sattva-prod-rust-transcoder-5c8d9f8c-x7k3m   1/1     Running   0          2m
sattva-prod-postgresql-0              1/1     Running   0          3m
sattva-prod-redis-master-0           1/1     Running   0          3m
```

---

## Configuration Options

### values.yaml Reference

The Helm chart is configured through `values.yaml`. Below are the key configuration sections:

#### Global Settings

```yaml
global:
  imageRegistry: "your-registry.com"  # Override image registry
  imagePullPolicy: IfNotPresent       # Image pull policy
  env: {}                             # Common environment variables
```

#### Backend Configuration

```yaml
backend:
  enabled: true
  replicaCount: 2

  image:
    repository: sattva/backend
    tag: "1.0.0"
    pullPolicy: IfNotPresent

  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

  resources:
    limits:
      cpu: 1000m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi

  service:
    type: ClusterIP
    port: 8000

  env:
    DATABASE_URL: "postgresql://postgres:password@postgresql:5432/telegram_db"
    REDIS_URL: "redis://redis-master:6379"

  secretEnv:
    JWT_SECRET: "jwt-secret"
    GOOGLE_DRIVE_API_KEY: "google-drive-api-key"
```

#### Frontend Configuration

```yaml
frontend:
  enabled: true
  replicaCount: 2

  image:
    repository: sattva/frontend
    tag: "1.0.0"

  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 6
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

  buildArgs:
    VITE_API_BASE_URL: "https://sattva-streamer.top"
    VITE_API_URL: "https://sattva-streamer.top"
    VITE_ENABLE_BASIC_LOGIN: "false"
```

#### Streamer Configuration

```yaml
streamer:
  enabled: true
  replicaCount: 1

  image:
    repository: sattva/streamer
    tag: "1.0.0"

  persistence:
    enabled: true
    size: 1Gi
    storageClass: ""

  env:
    REDIS_URL: "redis://redis-master:6379"
    BACKEND_URL: "http://backend:8000"
    CHAT_ID: "3211053168"
    VIDEO_QUALITY: "720p"
```

#### Database Configuration

```yaml
postgresql:
  enabled: true
  auth:
    postgresPassword: "sattva_db_pass_2025_9f3c0f"
    database: "telegram_db"
  primary:
    persistence:
      enabled: true
      size: 10Gi
      storageClass: ""

redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: false
  master:
    persistence:
      enabled: true
      size: 5Gi
```

#### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"

  frontend:
    enabled: true
    hostname: "sattva-streamer.top"
    tls: true

  backend:
    enabled: true
    hostname: "api.sattva-streamer.top"
    tls: true
```

### Custom values Files

Create environment-specific values files:

**values-dev.yaml:**
```yaml
backend:
  replicaCount: 1
  autoscaling:
    enabled: false
  resources:
    limits:
      cpu: 500m
      memory: 256Mi
    requests:
      cpu: 100m
      memory: 128Mi

frontend:
  replicaCount: 1
  autoscaling:
    enabled: false

ingress:
  backend:
    hostname: "api-dev.sattva-streamer.top"
  frontend:
    hostname: "dev.sattva-streamer.top"
```

**values-staging.yaml:**
```yaml
backend:
  replicaCount: 2
  autoscaling:
    minReplicas: 2
    maxReplicas: 5

frontend:
  replicaCount: 2
  autoscaling:
    minReplicas: 2
    maxReplicas: 4

ingress:
  backend:
    hostname: "api-staging.sattva-streamer.top"
  frontend:
    hostname: "staging.sattva-streamer.top"
```

**values-prod.yaml:**
```yaml
backend:
  replicaCount: 3
  autoscaling:
    minReplicas: 3
    maxReplicas: 10

frontend:
  replicaCount: 3
  autoscaling:
    minReplicas: 3
    maxReplicas: 6

ingress:
  backend:
    hostname: "api.sattva-streamer.top"
  frontend:
    hostname: "sattva-streamer.top"
```

---

## Environment-Specific Settings

### Development Environment

**Purpose:** Local testing and feature development

**Characteristics:**
- Single replica for most services
- Minimal resource allocation
- Autoscaling disabled
- Debug logging enabled
- No TLS/SSL (using HTTP)

**Deployment:**
```bash
helm install sattva-dev helm/sattva-streamer \
  --namespace sattva-dev \
  --values helm/sattva-streamer/values.yaml \
  --values helm/sattva-streamer/values-dev.yaml
```

### Staging Environment

**Purpose:** Pre-production testing and QA

**Characteristics:**
- Multiple replicas (2-3)
- Moderate resource allocation
- Autoscaling enabled with conservative limits
- Info-level logging
- TLS/SSL enabled
- Production-like configuration

**Deployment:**
```bash
helm install sattva-staging helm/sattva-streamer \
  --namespace sattva-staging \
  --values helm/sattva-streamer/values.yaml \
  --values helm/sattva-streamer/values-staging.yaml
```

### Production Environment

**Purpose:** Live production traffic

**Characteristics:**
- Multiple replicas (3+)
- Full resource allocation
- Autoscaling enabled with aggressive limits
- Warn/error-level logging
- TLS/SSL required
- High availability configuration
- Pod anti-affinity rules
- Pod disruption budgets

**Deployment:**
```bash
helm install sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --values helm/sattva-streamer/values.yaml \
  --values helm/sattva-streamer/values-prod.yaml
```

### Environment Comparison

| Feature | Dev | Staging | Production |
|---------|-----|---------|------------|
| **Replicas** | 1 | 2-3 | 3+ |
| **Autoscaling** | Disabled | Conservative | Aggressive |
| **Resources** | Minimal | Moderate | Full |
| **TLS/SSL** | No | Yes | Yes |
| **Monitoring** | Basic | Standard | Full |
| **Backup** | None | Daily | Hourly + Daily |
| **HA** | No | Partial | Full |

---

## Troubleshooting Common Issues

### Helm Chart Errors

**Issue:** Helm chart installation fails with validation errors

**Diagnosis:**
```bash
helm lint helm/sattva-streamer
helm template sattva-prod helm/sattva-streamer --values helm/sattva-streamer/values-prod.yaml
```

**Solutions:**
1. Fix template syntax errors
2. Ensure all required values are provided
3. Check for deprecated API versions

### Image Pull Failures

**Issue:** Pods fail with `ErrImagePull` or `ImagePullBackOff`

**Diagnosis:**
```bash
kubectl describe pod <pod-name> --namespace=sattva-prod
kubectl get events --namespace=sattva-prod --sort-by='.lastTimestamp'
```

**Solutions:**
1. **Private registry authentication:**
```bash
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry> \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  --namespace=sattva-prod

# Add to values.yaml
imagePullSecrets:
  - name: regcred
```

2. **Verify image exists:**
```bash
docker pull sattva/backend:1.0.0
```

3. **Check image tag:**
```bash
kubectl get deployment sattva-prod-backend --namespace=sattva-prod -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Resource Quota Exceeded

**Issue:** Pods fail with `FailedScheduling` due to insufficient resources

**Diagnosis:**
```bash
kubectl describe pod <pod-name> --namespace=sattva-prod
kubectl describe nodes
```

**Solutions:**
1. **Check resource usage:**
```bash
kubectl top nodes
kubectl top pods --namespace=sattva-prod
```

2. **Reduce resource requests:**
```yaml
resources:
  requests:
    cpu: 100m  # Reduced from 250m
    memory: 128Mi  # Reduced from 256Mi
```

3. **Add more nodes to the cluster**

### Insufficient Memory/CPU

**Issue:** Pods are OOMKilled or CPU-throttled

**Diagnosis:**
```bash
kubectl logs <pod-name> --namespace=sattva-prod --previous
kubectl describe pod <pod-name> --namespace=sattva-prod
```

**Solutions:**
1. **Increase memory limits:**
```yaml
resources:
  limits:
    memory: 1Gi  # Increased from 512Mi
```

2. **Check for memory leaks:**
```bash
kubectl exec -it <pod-name> --namespace=sattva-prod -- top
```

### Database Connection Issues

**Issue:** Backend cannot connect to PostgreSQL

**Diagnosis:**
```bash
kubectl logs -l app=backend --namespace=sattva-prod
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- psql -U postgres -h postgresql -d telegram_db
```

**Solutions:**
1. **Verify database is ready:**
```bash
kubectl get pods -l app=postgresql --namespace=sattva-prod
```

2. **Check connection string:**
```bash
kubectl get secret sattva-backend-env --namespace=sattva-prod -o jsonpath='{.data.DATABASE_URL}' | base64 -d
```

3. **Verify network policies:**
```bash
kubectl get networkpolicy --namespace=sattva-prod
```

### Secrets Not Found

**Issue:** Pods fail to start with secret not found errors

**Diagnosis:**
```bash
kubectl describe pod <pod-name> --namespace=sattva-prod
kubectl get secrets --namespace=sattva-prod
```

**Solutions:**
1. **Create missing secrets:**
```bash
kubectl create secret generic <secret-name> \
  --from-literal=KEY=value \
  --namespace=sattva-prod
```

2. **Verify secret references in values.yaml:**
```yaml
secretEnv:
  JWT_SECRET: "jwt-secret"  # Must match actual secret name
```

---

## Upgrade Procedures

### Rolling Update Strategy

The Helm chart uses rolling updates for zero-downtime deployments:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

### Upgrading the Application

**Step 1: Update values.yaml (if needed)**
```bash
# Review changes
git diff helm/sattva-streamer/values.yaml
```

**Step 2: Backup current configuration**
```bash
helm get values sattva-prod --namespace=sattva-prod > sattva-prod-backup.yaml
```

**Step 3: Run pre-upgrade checks**
```bash
./scripts/k8s-health-check.sh sattva
```

**Step 4: Upgrade the release**
```bash
helm upgrade sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --values helm/sattva-streamer/values.yaml \
  --values helm/sattva-streamer/values-prod.yaml \
  --wait \
  --timeout 15m \
  --atomic  # Rollback on failure
```

**Step 5: Verify upgrade**
```bash
helm status sattva-prod --namespace=sattva-prod
kubectl rollout status deployment/sattva-prod-backend --namespace=sattva-prod
kubectl get pods --namespace=sattva-prod
./scripts/k8s-health-check.sh sattva
```

### Upgrading Individual Services

```bash
# Upgrade only backend
helm upgrade sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --set backend.image.tag="1.1.0" \
  --reuse-values

# Upgrade only frontend
helm upgrade sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --set frontend.image.tag="1.1.0" \
  --reuse-values
```

### Database Migrations

For database schema changes:

```bash
# Run migrations manually
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- alembic upgrade head

# Or use a migration job
kubectl apply -f helm/sattva-streamer/templates/migrations-job.yaml
```

### Rollback Procedure

If an upgrade fails:

```bash
# List revisions
helm history sattva-prod --namespace=sattva-prod

# Rollback to previous version
helm rollback sattva-prod --namespace=sattva-prod

# Rollback to specific revision
helm rollback sattva-prod 2 --namespace=sattva-prod

# Verify rollback
helm status sattva-prod --namespace=sattva-prod
kubectl get pods --namespace=sattva-prod
```

---

## Uninstall Procedures

### Graceful Shutdown

**Step 1: Scale down to zero**
```bash
kubectl scale deployment sattva-prod-backend --replicas=0 --namespace=sattva-prod
kubectl scale deployment sattva-prod-frontend --replicas=0 --namespace=sattva-prod
kubectl scale deployment sattva-prod-rust-transcoder --replicas=0 --namespace=sattva-prod
```

**Step 2: Wait for connections to drain**
```bash
# Monitor active connections
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- netstat -an | grep ESTABLISHED
```

**Step 3: Backup data (if needed)**
```bash
# Backup PostgreSQL
kubectl exec sattva-prod-postgresql-0 --namespace=sattva-prod -- pg_dump -U postgres telegram_db > backup.sql

# Backup Redis
kubectl exec sattva-prod-redis-master-0 --namespace=sattva-prod -- redis-cli SAVE
kubectl cp sattva-prod-redis-master-0:/data/dump.rdb ./redis-backup.rdb --namespace=sattva-prod
```

### Complete Uninstallation

**Step 1: Uninstall the Helm release**
```bash
helm uninstall sattva-prod --namespace sattva-prod
```

**Step 2: Delete persistent volumes (if desired)**
```bash
# List PVCs
kubectl get pvc --namespace=sattva-prod

# Delete PVCs (WARNING: Data will be lost!)
kubectl delete pvc --all --namespace=sattva-prod
```

**Step 3: Delete secrets (if desired)**
```bash
kubectl delete secrets --all --namespace=sattva-prod
```

**Step 4: Delete the namespace**
```bash
kubectl delete namespace sattva-prod
```

### Selective Removal

Remove specific components:

```bash
# Remove only frontend
helm upgrade sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --set frontend.enabled=false \
  --reuse-values

# Remove only monitoring
helm upgrade sattva-prod helm/sattva-streamer \
  --namespace sattva-prod \
  --set monitoring.serviceMonitor.enabled=false \
  --reuse-values
```

---

## Additional Resources

### Useful Commands

```bash
# Port forward to local machine
kubectl port-forward svc/sattva-prod-backend 8000:8000 --namespace=sattva-prod
kubectl port-forward svc/sattva-prod-frontend 3000:80 --namespace=sattva-prod

# Execute commands in pods
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- /bin/bash
kubectl exec -it sattva-prod-postgresql-0 --namespace=sattva-prod -- psql -U postgres

# Watch pod status
watch kubectl get pods --namespace=sattva-prod

# Get pod logs (follow)
kubectl logs -f sattva-prod-backend-xxx --namespace=sattva-prod

# Get logs for all pods in a deployment
kubectl logs -l app=backend --namespace=sattva-prod --tail=100

# Describe resources
kubectl describe deployment sattva-prod-backend --namespace=sattva-prod
kubectl describe service sattva-prod-backend --namespace=sattva-prod
kubectl describe ingress sattva-prod --namespace=sattva-prod

# Get YAML for deployed resources
kubectl get deployment sattva-prod-backend --namespace=sattva-prod -o yaml

# Get resource usage
kubectl top pods --namespace=sattva-prod
kubectl top nodes
```

### Monitoring and Observability

```bash
# View events
kubectl get events --namespace=sattva-prod --sort-by='.lastTimestamp'

# View pod metrics
kubectl get pods --namespace=sattva-prod -o custom-columns=NAME:.metadata.name,CPU:.status.containerStatuses[0].state.running.startedAt

# View resource allocation
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### Debugging Tips

1. **Always check pod events first:**
   ```bash
   kubectl describe pod <pod-name> --namespace=sattva-prod
   ```

2. **Use stern for log aggregation:**
   ```bash
   stern -n sattva-prod backend
   ```

3. **Use k9s for interactive monitoring:**
   ```bash
   k9s -n sattva-prod
   ```

4. **Verify DNS resolution:**
   ```bash
   kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup postgresql.sattva-prod.svc.cluster.local
   ```

5. **Test network connectivity:**
   ```bash
   kubectl run -it --rm debug --image=busybox --restart=Never -- wget -O- http://backend:8000/api/health
   ```

---

## Support and Documentation

For additional help:

- **GitHub Issues**: https://github.com/sattva-streamer/sattva/issues
- **Documentation**: https://docs.sattva-streamer.top
- **Email**: dev@sattva-streamer.top

---

**Last Updated:** 2025-01-23
**Document Version:** 1.0.0
