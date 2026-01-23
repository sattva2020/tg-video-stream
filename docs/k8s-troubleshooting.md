# Kubernetes Troubleshooting Guide for Sattva Streamer

This comprehensive guide covers common issues, diagnostic procedures, and solutions for troubleshooting Kubernetes deployments of Sattva Telegram Streamer.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Runtime Issues](#runtime-issues)
- [Autoscaling Issues](#autoscaling-issues)
- [Networking Issues](#networking-issues)
- [Storage Issues](#storage-issues)
- [Performance Issues](#performance-issues)
- [Debugging Commands Reference](#debugging-commands-reference)

---

## Installation Issues

### Helm Chart Errors

#### Issue: Helm Chart Lint Fails

**Symptoms:**
```bash
$ helm lint helm/sattva-streamer
ERROR: YAML parse error on helm/sattva-streamer/templates/backend/deployment.yaml
```

**Diagnosis:**
```bash
# Check YAML syntax
helm lint helm/sattva-streamer --debug

# Validate templates
helm template sattva-prod helm/sattva-streamer --values helm/sattva-streamer/values-prod.yaml
```

**Solutions:**

1. **Fix YAML indentation:**
```yaml
# Wrong
resources:
limits:
  cpu: 1000m

# Correct
resources:
  limits:
    cpu: 1000m
```

2. **Fix template syntax:**
```yaml
# Wrong
{{ if .Values.enabled }}
# Correct
{{- if .Values.enabled }}
```

3. **Use yamllint for validation:**
```bash
pip install yamllint
yamllint helm/sattva-streamer/templates/
```

#### Issue: Helm Install Fails with Validation Error

**Symptoms:**
```bash
Error: validation failed: unable to recognize "": no matches for kind "HorizontalPodAutoscaler" in version "autoscaling/v2beta1"
```

**Diagnosis:**
```bash
# Check Kubernetes version
kubectl version --short

# Check available API versions
kubectl api-versions | grep autoscaling
```

**Solutions:**

1. **Update API version:**
```yaml
# Change from autoscaling/v2beta1
apiVersion: autoscaling/v2beta1

# To autoscaling/v2
apiVersion: autoscaling/v2
```

2. **Update Helm chart for Kubernetes version:**
```bash
# Check Kubernetes version compatibility
helm version --short
kubectl version --short
```

3. **Use compatible chart version:**
```bash
# List available chart versions
helm search repo sattva-streamer --versions

# Install specific version
helm install sattva-prod helm/sattva-streamer --version 0.1.0
```

### Image Pull Failures

#### Issue: ErrImagePull or ImagePullBackOff

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS             RESTARTS   AGE
sattva-prod-backend-xxx           0/1     ImagePullBackOff   0          2m
```

**Diagnosis:**
```bash
# Describe pod for detailed error
kubectl describe pod sattva-prod-backend-xxx --namespace=sattva-prod

# Check events
kubectl get events --namespace=sattva-prod --sort-by='.lastTimestamp'

# View image pull errors
kubectl logs sattva-prod-backend-xxx --namespace=sattva-prod
```

**Solutions:**

1. **Private registry authentication:**
```bash
# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry> \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  --docker-email=<your-email> \
  --namespace=sattva-prod

# Add to deployment
kubectl patch deployment sattva-prod-backend --namespace=sattva-prod \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

2. **Verify image exists:**
```bash
# Test image pull locally
docker pull sattva/backend:1.0.0

# List available tags
docker search sattva/backend
```

3. **Check image tag:**
```bash
# Get current image
kubectl get deployment sattva-prod-backend --namespace=sattva-prod -o jsonpath='{.spec.template.spec.containers[0].image}'

# Update image tag
kubectl set image deployment/sattva-prod-backend backend=sattva/backend:1.0.1 --namespace=sattva-prod
```

4. **Fix image name:**
```yaml
# Wrong
image: sattva-backend:latest

# Correct
image: sattva/backend:1.0.0
```

#### Issue: Image Pull Rate Limit Exceeded

**Symptoms:**
```bash
Failed to pull image "library/postgres:14": rpc error: code = Unknown desc = Error response from daemon: toomanyrequests: You have reached your pull rate limit.
```

**Diagnosis:**
```bash
# Check Docker Hub rate limit
curl -I https://registry-1.docker.io/v2/library/postgres/manifests/latest
```

**Solutions:**

1. **Use authenticated pulls:**
```bash
# Login to Docker Hub
docker login

# Create secret with credentials
kubectl create secret docker-registry dockerhub-credentials \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  --namespace=sattva-prod
```

2. **Use alternative registry:**
```yaml
# Use mirror registry
image: mirror.docker.io/library/postgres:14

# Or use your own registry
image: registry.sattva-streamer.top/postgres:14
```

3. **Use specific tags instead of latest:**
```yaml
# Avoid
image: postgres:latest

# Use
image: postgres:14.5
```

### Resource Quota Exceeded

#### Issue: Pod Fails with FailedScheduling

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS    RESTARTS   AGE
sattva-prod-backend-xxx           0/1     Pending   0          5m

$ kubectl describe pod sattva-prod-backend-xxx
Warning  FailedScheduling  pod(s) exceeded quota
```

**Diagnosis:**
```bash
# Check resource quotas
kubectl get resourcequota --namespace=sattva-prod

# Check used resources
kubectl describe resourcequota compute-resources --namespace=sattva-prod

# Check limit ranges
kubectl get limitrange --namespace=sattva-prod
```

**Solutions:**

1. **Increase resource quota:**
```bash
# Edit resource quota
kubectl edit resourcequota compute-resources --namespace=sattva-prod

# Example increase
spec:
  hard:
    requests.cpu: "8"  # Increased from "4"
    requests.memory: "16Gi"  # Increased from "8Gi"
```

2. **Reduce resource requests:**
```yaml
# Update values.yaml
resources:
  requests:
    cpu: 100m  # Reduced from 250m
    memory: 128Mi  # Reduced from 256Mi
```

3. **Delete unused deployments:**
```bash
# List all deployments
kubectl get deployments --namespace=sattva-prod

# Delete unused deployments
kubectl delete deployment old-deployment --namespace=sattva-prod
```

4. **Add more nodes to cluster:**
```bash
# Using cloud provider CLI
# AWS example
aws eks --region us-east-1 update-nodegroup-config \
  --cluster-name sattva-prod \
  --nodegroup-name standard-workers \
  --scaling-config desiredSize=10
```

### Insufficient Memory/CPU

#### Issue: Pod OOMKilled

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS      RESTARTS   AGE
sattva-prod-backend-xxx           0/1     OOMKilled   3          10m

$ kubectl describe pod sattva-prod-backend-xxx
Last State:  Terminated
  Reason:    OOMKilled
  Exit Code: 137
```

**Diagnosis:**
```bash
# Check pod metrics
kubectl top pod sattva-prod-backend-xxx --namespace=sattva-prod

# Check container limits
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.containers[0].resources}'

# View previous logs
kubectl logs sattva-prod-backend-xxx --namespace=sattva-prod --previous
```

**Solutions:**

1. **Increase memory limit:**
```yaml
# Update values.yaml
resources:
  limits:
    memory: 1Gi  # Increased from 512Mi
  requests:
    memory: 512Mi  # Increased from 256Mi
```

2. **Check for memory leaks:**
```bash
# Connect to container
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- /bin/bash

# Check memory usage
top
free -m
cat /sys/fs/cgroup/memory/memory.limit_in_bytes
cat /sys/fs/cgroup/memory/memory.usage_in_bytes
```

3. **Optimize application:**
```python
# Add memory profiling
import tracemalloc
tracemalloc.start()

# Take snapshot
snapshot1 = tracemalloc.take_snapshot()

# Compare later
snapshot2 = tracemalloc.take_snapshot()
top_stats = snapshot2.compare_to(snapshot1, 'lineno')
```

#### Issue: CPU Throttling

**Symptoms:**
```bash
# Application slow to respond
# High CPU usage but limited performance
```

**Diagnosis:**
```bash
# Check CPU usage
kubectl top pod sattva-prod-backend-xxx --namespace=sattva-prod --containers=true

# Check CPU throttling
kubectl exec sattva-prod-backend-xxx --namespace=sattva-prod -- cat /sys/fs/cgroup/cpu/cpu.stat

# Look for 'nr_throttled' and 'throttled_time'
```

**Solutions:**

1. **Increase CPU limit:**
```yaml
resources:
  limits:
    cpu: 2000m  # Increased from 1000m
  requests:
    cpu: 500m  # Increased from 250m
```

2. **Check for CPU-intensive tasks:**
```bash
# Connect to container
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- /bin/bash

# Check CPU usage
top -H
ps aux --sort=-%cpu | head
```

---

## Runtime Issues

### Pods in CrashLoopBackOff

#### Issue: Container Repeatedly Crashes

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS                 RESTARTS   AGE
sattva-prod-backend-xxx           0/1     CrashLoopBackOff       5          10m
```

**Diagnosis:**
```bash
# Describe pod
kubectl describe pod sattva-prod-backend-xxx --namespace=sattva-prod

# View logs
kubectl logs sattva-prod-backend-xxx --namespace=sattva-prod

# View previous logs
kubectl logs sattva-prod-backend-xxx --namespace=sattva-prod --previous

# Check events
kubectl get events --namespace=sattva-prod --sort-by='.lastTimestamp'
```

**Common Causes and Solutions:**

1. **Application error:**
```bash
# Check application logs
kubectl logs sattva-prod-backend-xxx --namespace=sattva-prod

# Fix application bug
# Push new image
# Update deployment
kubectl set image deployment/sattva-prod-backend backend=sattva/backend:1.0.1 --namespace=sattva-prod
```

2. **Missing environment variables:**
```bash
# Check required env vars
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- env | grep DATABASE

# Add missing env vars
kubectl set env deployment/sattva-prod-backend DATABASE_URL=postgresql://... --namespace=sattva-prod
```

3. **Missing config file:**
```bash
# Check for config files
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- ls -la /app/config

# Mount config volume
kubectl set volume deployment/sattva-prod-backend --add -t /app/config --source=configMap/config --namespace=sattva-prod
```

4. **Database connection failure:**
```bash
# Test database connection
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- psql -U postgres -h postgresql telegram_db

# Fix connection string
kubectl set env deployment/sattva-prod-backend DATABASE_URL=postgresql://postgres:password@postgresql:5432/telegram_db --namespace=sattva-prod
```

### Pods Stuck in Pending State

#### Issue: Pod Never Schedules

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS    RESTARTS   AGE
sattva-prod-backend-xxx           0/1     Pending   0          10m
```

**Diagnosis:**
```bash
# Describe pod
kubectl describe pod sattva-prod-backend-xxx --namespace=sattva-prod

# Check events
kubectl get events --namespace=sattva-prod --sort-by='.lastTimestamp'

# Check node resources
kubectl describe nodes
```

**Common Causes and Solutions:**

1. **Insufficient resources:**
```bash
# Check node resources
kubectl top nodes

# Add more nodes
# (See "Resource Quota Exceeded" section)
```

2. **Node selector not matching:**
```bash
# Check node selector
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.nodeSelector}'

# Check available nodes
kubectl get nodes --show-labels

# Fix node selector
kubectl label node <node-name> app=backend
```

3. **Taints and tolerations:**
```bash
# Check node taints
kubectl describe nodes | grep Taints

# Check pod tolerations
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.tolerations}'

# Add toleration
kubectl patch deployment sattva-prod-backend --namespace=sattva-prod -p '{"spec":{"template":{"spec":{"tolerations":[{"key":"key","operator":"Equal","value":"value","effect":"NoSchedule"}]}}}}'
```

4. **Persistent volume not binding:**
```bash
# Check PVC
kubectl get pvc --namespace=sattva-prod

# Check PV
kubectl get pv

# Check storage class
kubectl get storageclass

# Fix storage class
kubectl patch pvc data-pvc --namespace=sattva-prod -p '{"spec":{"storageClassName":"standard"}}'
```

### High Memory/CPU Usage

#### Issue: Pod Consumes Excessive Resources

**Symptoms:**
```bash
$ kubectl top pods --namespace=sattva-prod
NAME                              CPU(cores)   MEMORY(bytes)
sattva-prod-backend-xxx           1500m        2Gi
```

**Diagnosis:**
```bash
# Check resource usage
kubectl top pod sattva-prod-backend-xxx --namespace=sattva-prod --containers=true

# Check processes inside container
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- top

# Check resource limits
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.containers[0].resources}'
```

**Solutions:**

1. **Identify the cause:**
```bash
# Profile memory usage
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- python -m memory_profiler app.py

# Profile CPU usage
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- python -m cProfile app.py
```

2. **Optimize application code**
3. **Add resource limits:**
```yaml
resources:
  limits:
    cpu: 1000m
    memory: 512Mi
```

4. **Scale horizontally:**
```bash
kubectl scale deployment sattva-prod-backend --replicas=5 --namespace=sattva-prod
```

### Health Check Failures

#### Issue: Liveness Probe Failing

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS    RESTARTS   AGE
sattva-prod-backend-xxx           1/1     Running   10         10m

$ kubectl describe pod sattva-prod-backend-xxx
Warning  Unhealthy  Liveness probe failed: HTTP probe failed with statuscode: 500
```

**Diagnosis:**
```bash
# Check probe configuration
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.containers[0].livenessProbe}'

# Test endpoint manually
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- curl localhost:8000/api/health/live

# Check application logs
kubectl logs sattva-prod-backend-xxx --namespace=sattva-prod
```

**Solutions:**

1. **Fix health endpoint:**
```python
# Ensure endpoint returns 200
@app.get("/api/health/live")
async def liveness():
    return {"status": "alive"}
```

2. **Adjust probe settings:**
```yaml
livenessProbe:
  httpGet:
    path: /api/health/live
    port: http
  initialDelaySeconds: 60  # Increased from 30
  periodSeconds: 20  # Increased from 10
  timeoutSeconds: 10  # Increased from 5
  failureThreshold: 5  # Increased from 3
```

3. **Check for deadlocks:**
```bash
# Connect to container
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- /bin/bash

# Check for hung processes
ps aux
strace -p <pid>
```

#### Issue: Readiness Probe Failing

**Symptoms:**
```bash
$ kubectl get pods
NAME                              READY   STATUS    RESTARTS   AGE
sattva-prod-backend-xxx           0/1     Running   0          5m

$ kubectl describe pod sattva-prod-backend-xxx
Warning  Unhealthy  Readiness probe failed: HTTP probe failed with statuscode: 503
```

**Diagnosis:**
```bash
# Check probe configuration
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.containers[0].readinessProbe}'

# Test endpoint manually
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- curl localhost:8000/api/health/ready
```

**Solutions:**

1. **Fix readiness endpoint:**
```python
@app.get("/api/health/ready")
async def readiness():
    # Check database connection
    try:
        db.execute("SELECT 1")
    except:
        raise HTTPException(status_code=503, detail="Database not ready")

    # Check Redis connection
    try:
        redis.ping()
    except:
        raise HTTPException(status_code=503, detail="Redis not ready")

    return {"status": "ready"}
```

2. **Adjust probe settings:**
```yaml
readinessProbe:
  httpGet:
    path: /api/health/ready
    port: http
  initialDelaySeconds: 30  # Increased from 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 5  # Increased from 3
```

---

## Autoscaling Issues

### HPA Not Scaling Up

#### Issue: HPA Doesn't Create More Pods

**Symptoms:**
```bash
$ kubectl get hpa
NAME                     REFERENCE                       TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
sattva-prod-backend      Deployment/sattva-prod-backend 80%/70%         2         10        2          1h

# CPU at 80% but not scaling
```

**Diagnosis:**
```bash
# Describe HPA
kubectl describe hpa sattva-prod-backend --namespace=sattva-prod

# Check current metrics
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/sattva-prod/pods | jq .

# Check metrics server
kubectl get pods -n kube-system -l k8s-app=metrics-server

# Check resource requests
kubectl get pod sattva-prod-backend-xxx --namespace=sattva-prod -o jsonpath='{.spec.containers[0].resources.requests}'
```

**Common Causes and Solutions:**

1. **Metrics server not running:**
```bash
# Check metrics server
kubectl get pods -n kube-system -l k8s-app=metrics-server

# Restart metrics server
kubectl rollout restart deployment/metrics-server -n kube-system
```

2. **Resource requests not set:**
```yaml
# Add resource requests
resources:
  requests:
    cpu: 250m
    memory: 256Mi
```

3. **Already at max replicas:**
```bash
# Check max replicas
kubectl get hpa sattva-prod-backend --namespace=sattva-prod

# Increase max replicas
kubectl edit hpa sattva-prod-backend --namespace=sattva-prod
```

4. **Insufficient cluster capacity:**
```bash
# Check cluster capacity
kubectl describe nodes

# Add more nodes or increase maxReplicas
```

5. **Metrics not available:**
```bash
# Check metrics API
kubectl get --raw /apis/metrics.k8s.io/v1beta1

# Install metrics server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### HPA Scaling Too Aggressively

#### Issue: Pods Constantly Scale Up and Down

**Symptoms:**
```bash
$ kubectl get hpa
NAME                     REFERENCE                       TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
sattva-prod-backend      Deployment/sattva-prod-backend 70%/70%  2         10        5          10m
# Replicas keeps changing
```

**Diagnosis:**
```bash
# Describe HPA
kubectl describe hpa sattva-prod-backend --namespace=sattva-prod

# Check HPA behavior
kubectl get hpa sattva-prod-backend --namespace=sattva-prod -o yaml | grep -A 20 behavior:

# Check events
kubectl get events --namespace=sattva-prod | grep HorizontalPodAutoscaler
```

**Solutions:**

1. **Increase stabilization window:**
```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 600  # 10 minutes
  scaleUp:
    stabilizationWindowSeconds: 60   # 1 minute
```

2. **Adjust scaling policies:**
```yaml
behavior:
  scaleDown:
    policies:
      - type: Percent
        value: 50  # Reduce by half
        periodSeconds: 60
  scaleUp:
    policies:
      - type: Pods
        value: 1  # Add 1 pod at a time
        periodSeconds: 60
```

3. **Adjust target thresholds:**
```yaml
autoscaling:
  targetCPUUtilizationPercentage: 80  # Increased from 70
  targetMemoryUtilizationPercentage: 85  # Increased from 80
```

### Metrics Not Available

#### Issue: Custom Metrics Not Working

**Symptoms:**
```bash
$ kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1
Error: the server doesn't have a resource type "custom.metrics.k8s.io"
```

**Diagnosis:**
```bash
# Check Prometheus Adapter
kubectl get pods -n monitoring -l name=prometheus-adapter

# Check custom metrics API
kubectl get apiservices | grep custom

# Check Prometheus Adapter logs
kubectl logs -n monitoring -l name=prometheus-adapter
```

**Solutions:**

1. **Install Prometheus Adapter:**
```bash
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  --namespace monitoring \
  --values prometheus-adapter-values.yaml
```

2. **Configure custom metrics:**
```yaml
# prometheus-adapter-values.yaml
rules:
  default: true
  custom:
    - seriesQuery: '{__name__=~"^active_streams_.*"}'
      resources:
        overrides:
          namespace: {resource: "namespace"}
          pod: {resource: "pod"}
      name:
        matches: "^(.*)_total"
        as: "active_streams"
      metricsQuery: "sum(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)"
```

3. **Verify Prometheus is exposing metrics:**
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus-operated 9090:9090 -n monitoring

# Open http://localhost:9090/targets
# Verify backend is being scraped
```

---

## Networking Issues

### Services Not Reachable

#### Issue: Service Endpoint Not Accessible

**Symptoms:**
```bash
$ kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- curl frontend:80
curl: (7) Failed to connect to frontend port 80: Connection refused
```

**Diagnosis:**
```bash
# Check service
kubectl get svc frontend --namespace=sattva-prod

# Describe service
kubectl describe svc frontend --namespace=sattva-prod

# Check endpoints
kubectl get endpoints frontend --namespace=sattva-prod

# Check pod selectors
kubectl get pods --namespace=sattva-prod -l app=frontend
```

**Common Causes and Solutions:**

1. **Wrong service type:**
```yaml
# Change from ClusterIP to NodePort for testing
service:
  type: NodePort
  port: 80
```

2. **Selector mismatch:**
```yaml
# Ensure service selector matches pod labels
service:
  selector:
    app: frontend  # Must match pod labels
```

3. **Port mismatch:**
```yaml
# Ensure service port matches container port
service:
  port: 80
  targetPort: http  # Must match containerPort name

containerPort: 80
name: http
```

4. **Network policy blocking:**
```bash
# Check network policies
kubectl get networkpolicy --namespace=sattva-prod

# Allow traffic
kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-frontend
  namespace: sattva-prod
spec:
  podSelector:
    matchLabels:
      app: frontend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 80
EOF
```

### Ingress Not Working

#### Issue: Ingress Returns 404 or 502

**Symptoms:**
```bash
$ curl https://api.sattva-streamer.top/api/health
404 Not Found

# or

502 Bad Gateway
```

**Diagnosis:**
```bash
# Check ingress
kubectl get ingress --namespace=sattva-prod

# Describe ingress
kubectl describe ingress sattva-prod --namespace=sattva-prod

# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

**Common Causes and Solutions:**

1. **Ingress controller not running:**
```bash
# Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

2. **Wrong ingress class:**
```yaml
ingress:
  className: "nginx"  # Ensure this matches your ingress controller
```

3. **Service not found:**
```bash
# Check service exists
kubectl get svc backend --namespace=sattva-prod

# Verify service name in ingress
kubectl get ingress sattva-prod --namespace=sattva-prod -o yaml | grep serviceName
```

4. **Path mismatch:**
```yaml
ingress:
  backend:
    path: /api  # Ensure this matches application routes
    pathType: Prefix
```

5. **TLS certificate issue:**
```bash
# Check certificate
kubectl get secret sattva-backend-tls --namespace=sattva-prod

# Verify cert-manager
kubectl get pods -n cert-manager

# Check certificate status
kubectl get certificate --namespace=sattva-prod
```

### TLS Certificate Errors

#### Issue: Certificate Not Ready

**Symptoms:**
```bash
$ kubectl get certificate
NAME                     READY   SECRET           AGE
sattva-backend-tls       False   sattva-backend-tls   1h
```

**Diagnosis:**
```bash
# Describe certificate
kubectl describe certificate sattva-backend-tls --namespace=sattva-prod

# Check cert-manager
kubectl get pods -n cert-manager

# Check certificate request
kubectl get certificaterequest --namespace=sattva-prod

# Check order
kubectl get order --namespace=sattva-prod

# Check challenge
kubectl get challenge --namespace=sattva-prod
```

**Common Causes and Solutions:**

1. **Cluster issuer not configured:**
```bash
# Create cluster issuer
kubectl apply -f - << EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@sattva-streamer.top
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

2. **Ingress not reachable:**
```bash
# Check DNS resolution
nslookup api.sattva-streamer.top

# Check ingress controller
kubectl get svc -n ingress-nginx

# Ensure ingress is exposed
kubectl patch svc ingress-nginx-controller -n ingress-nginx -p '{"spec":{"type":"LoadBalancer"}}'
```

3. **Rate limiting:**
```bash
# Let's Encrypt rate limits
# Wait 1 hour before retrying
# Or use staging issuer for testing
```

### DNS Resolution Failures

#### Issue: Pod Cannot Resolve Service Names

**Symptoms:**
```bash
$ kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- nslookup postgresql
Server:    10.96.0.10
Address:   10.96.0.10:53

** server can't find postgresql: NXDOMAIN
```

**Diagnosis:**
```bash
# Check DNS configuration
kubectl exec -it sattva-prod-backend-xxx --namespace=sattva-prod -- cat /etc/resolv.conf

# Check CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns

# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup postgresql.sattva-prod.svc.cluster.local
```

**Common Causes and Solutions:**

1. **Wrong service name:**
```bash
# Use fully qualified domain name
postgresql.sattva-prod.svc.cluster.local
```

2. **CoreDNS not running:**
```bash
# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system
```

3. **DNS search path issue:**
```yaml
# Add search path
dnsPolicy: "None"
dnsConfig:
  searches:
    - sattva-prod.svc.cluster.local
    - svc.cluster.local
    - cluster.local
```

4. **Custom DNS server:**
```yaml
dnsPolicy: "None"
dnsConfig:
  nameservers:
    - 8.8.8.8
    - 8.8.4.4
```

---

## Storage Issues

### PVCs Not Binding

#### Issue: PersistentVolumeClaim Pending

**Symptoms:**
```bash
$ kubectl get pvc
NAME                      STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-postgresql-0         Pending                                      standard       10m
```

**Diagnosis:**
```bash
# Describe PVC
kubectl describe pvc data-postgresql-0 --namespace=sattva-prod

# Check storage class
kubectl get storageclass

# Check available PVs
kubectl get pv

# Check storage provisioner
kubectl get pods -n kube-system | grep provisioner
```

**Common Causes and Solutions:**

1. **Storage class not available:**
```bash
# Create storage class
kubectl apply -f - << EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
EOF
```

2. **No available PVs:**
```bash
# Create PV manually
kubectl apply -f - << EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  hostPath:
    path: /data/postgresql
EOF
```

3. **Wrong access mode:**
```yaml
# Change access mode
persistence:
  accessMode: ReadWriteOnce  # Most common for databases
```

4. **Insufficient resources:**
```bash
# Check disk space on nodes
kubectl describe nodes | grep Allocated

# Clean up unused PVs
kubectl delete pv <unused-pv>
```

### Storage Class Not Available

#### Issue: Cannot Find Storage Class

**Symptoms:**
```bash
$ kubectl get storageclass
No resources found
```

**Diagnosis:**
```bash
# Check cloud provider
kubectl get sc

# Check for dynamic provisioning
kubectl get pods -n kube-system | grep provisioner
```

**Solutions:**

1. **Install storage provisioner:**
```bash
# For local testing
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.22/deploy/local-path-storage.yaml

# For AWS EKS
# EBS provisioner is installed by default
```

2. **Use hostPath for testing:**
```yaml
# Only for testing!
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: host-path
provisioner: rancher.io/local-path
```

### Disk Space Issues

#### Issue: Volume Full

**Symptoms:**
```bash
$ kubectl exec -it postgresql-0 -- df -h
Filesystem      Size  Used Avail Use% Mounted on
/dev/xvda1      9.8G  9.7G   0M  100% /data
```

**Diagnosis:**
```bash
# Check volume usage
kubectl exec -it postgresql-0 -- df -h

# Check PVC size
kubectl get pvc data-postgresql-0 --namespace=sattva-prod

# Check what's using space
kubectl exec -it postgresql-0 -- du -sh /data/*
```

**Solutions:**

1. **Expand PVC:**
```yaml
# Edit PVC to increase size
kubectl edit pvc data-postgresql-0 --namespace=sattva-prod

# Change size from 10Gi to 20Gi
```

2. **Clean up old data:**
```bash
# Connect to pod
kubectl exec -it postgresql-0 --namespace=sattva-prod -- /bin/bash

# Clean up logs
find /var/log -name "*.log" -mtime +7 -delete

# Clean up temp files
rm -rf /tmp/*
```

3. **Configure log rotation:**
```yaml
# Add log rotation
volumeMounts:
  - name: logs
    mountPath: /var/log

volumes:
  - name: logs
    emptyDir: {}
    sizeLimit: 100Mi
```

---

## Performance Issues

### Slow Response Times

#### Issue: Application Responding Slowly

**Symptoms:**
```bash
$ time curl https://api.sattva-streamer.top/api/health
real    0m5.123s
```

**Diagnosis:**
```bash
# Check pod resource usage
kubectl top pods --namespace=sattva-prod

# Check pod logs
kubectl logs -l app=backend --namespace=sattva-prod --tail=100

# Check network latency
kubectl exec -it backend-xxx -- ping frontend

# Check database queries
kubectl exec -it postgresql-0 -- psql -U postgres telegram_db -c "SELECT * FROM pg_stat_activity;"
```

**Common Causes and Solutions:**

1. **Database slow queries:**
```bash
# Enable query logging
kubectl exec -it postgresql-0 -- psql -U postgres postgres -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# Restart PostgreSQL
kubectl rollout restart statefulset/postgresql --namespace=sattva-prod

# Check logs
kubectl logs postgresql-0 --namespace=sattva-prod | grep "duration:"
```

2. **Network latency:**
```bash
# Check pod-to-pod latency
kubectl exec -it backend-xxx -- ping frontend -c 10

# Check service latency
kubectl exec -it backend-xxx -- curl -w "@curl-format.txt" -o /dev/null -s frontend:80

# Use network policies to optimize routing
```

3. **Resource limits:**
```yaml
# Increase resource limits
resources:
  limits:
    cpu: 2000m
    memory: 1Gi
```

4. **Application code optimization:**
```python
# Add connection pooling
# Add caching
# Optimize database queries
# Add async operations
```

### High Latency

#### Issue: Intermittent High Latency

**Symptoms:**
```bash
$ for i in {1..10}; do time curl api.sattva-streamer.top/api/health; done
real    0m0.123s
real    0m0.456s
real    0m2.345s
```

**Diagnosis:**
```bash
# Monitor latency over time
kubectl exec -it backend-xxx -- while true; do curl -w "%{time_total}\n" -o /dev/null -s frontend:80; sleep 1; done

# Check for GC pauses
kubectl logs backend-xxx --namespace=sattva-prod | grep -i gc

# Check for database locks
kubectl exec -it postgresql-0 -- psql -U postgres telegram_db -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

**Solutions:**

1. **Connection pooling:**
```python
# Use connection pool
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

2. **Caching:**
```python
# Add Redis caching
import redis

redis_client = redis.Redis(host='redis', port=6379, db=0)

@cache(ttl=60)
def get_user(user_id):
    return db.query(User).filter(User.id == user_id).first()
```

3. **Load balancing:**
```yaml
# Use multiple replicas
replicaCount: 5

# Enable autoscaling
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
```

### Database Connection Issues

#### Issue: Too Many Database Connections

**Symptoms:**
```bash
$ kubectl logs backend-xxx --namespace=sattva-prod
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) FATAL: remaining connection slots are reserved
```

**Diagnosis:**
```bash
# Check current connections
kubectl exec -it postgresql-0 -- psql -U postgres telegram_db -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Check max connections
kubectl exec -it postgresql-0 -- psql -U postgres postgres -c "SHOW max_connections;"

# Check connection state
kubectl exec -it postgresql-0 -- psql -U postgres telegram_db -c "SELECT * FROM pg_stat_activity;"
```

**Solutions:**

1. **Increase max connections:**
```yaml
# Update PostgreSQL config
postgresql:
  primary:
    extraEnvVars:
      - name: POSTGRES_MAX_CONNECTIONS
        value: "200"
```

2. **Use connection pooling:**
```python
# Configure pool size
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

3. **Use PgBouncer:**
```yaml
# Add PgBouncer to deployment
pgbouncer:
  enabled: true
  poolMode: transaction
  maxClientConn: 200
  defaultPoolSize: 25
```

---

## Debugging Commands Reference

### kubectl Commands

#### Logs

```bash
# View pod logs
kubectl logs <pod-name> --namespace=<namespace>

# Follow logs
kubectl logs -f <pod-name> --namespace=<namespace>

# View previous container logs
kubectl logs <pod-name> --namespace=<namespace> --previous

# View logs for all pods in a deployment
kubectl logs -l app=<app-name> --namespace=<namespace>

# View logs with timestamps
kubectl logs <pod-name> --namespace=<namespace> --timestamps=true

# View logs since time
kubectl logs --since-time=2025-01-23T10:00:00Z <pod-name> --namespace=<namespace>
```

#### Describe

```bash
# Describe pod
kubectl describe pod <pod-name> --namespace=<namespace>

# Describe service
kubectl describe svc <service-name> --namespace=<namespace>

# Describe deployment
kubectl describe deployment <deployment-name> --namespace=<namespace>

# Describe HPA
kubectl describe hpa <hpa-name> --namespace=<namespace>

# Describe PVC
kubectl describe pvc <pvc-name> --namespace=<namespace>
```

#### Exec

```bash
# Execute command in pod
kubectl exec -it <pod-name> --namespace=<namespace> -- /bin/bash

# Execute single command
kubectl exec <pod-name> --namespace=<namespace> -- ls -la

# Execute command in specific container
kubectl exec -it <pod-name> --namespace=<namespace> -c <container-name> -- /bin/bash
```

#### Port Forward

```bash
# Port forward to local port
kubectl port-forward svc/<service-name> 8080:80 --namespace=<namespace>

# Port forward to pod
kubectl port-forward <pod-name> 8080:80 --namespace=<namespace>

# Port forward with specific protocol
kubectl port-forward svc/<service-name> 8080:80 --namespace=<namespace> --protocol=tcp
```

#### Get

```bash
# Get all pods
kubectl get pods --namespace=<namespace>

# Get pods with wide output
kubectl get pods --namespace=<namespace> -o wide

# Get pods with labels
kubectl get pods --namespace=<namespace> -l app=<app-name>

# Get resources as YAML
kubectl get pod <pod-name> --namespace=<namespace> -o yaml

# Get resources as JSON
kubectl get pod <pod-name> --namespace=<namespace> -o json

# Get specific field
kubectl get pod <pod-name> --namespace=<namespace> -o jsonpath='{.spec.nodeName}'
```

### Helm Commands

```bash
# List releases
helm list --namespace=<namespace>

# Get release status
helm status <release-name> --namespace=<namespace>

# Get release values
helm get values <release-name> --namespace=<namespace>

# Get release manifest
helm get manifest <release-name> --namespace=<namespace>

# Get release hooks
helm get hooks <release-name> --namespace=<namespace>

# Get release history
helm history <release-name> --namespace=<namespace>

# Rollback release
helm rollback <release-name> --namespace=<namespace>

# Upgrade release
helm upgrade <release-name> <chart-path> --namespace=<namespace>

# Uninstall release
helm uninstall <release-name> --namespace=<namespace>

# Debug template
helm template <release-name> <chart-path> --namespace=<namespace>

# Lint chart
helm lint <chart-path>

# Test release
helm test <release-name> --namespace=<namespace>
```

### Checking Events

```bash
# Get all events
kubectl get events --namespace=<namespace>

# Get events sorted by time
kubectl get events --namespace=<namespace> --sort-by='.lastTimestamp'

# Get events for specific object
kubectl get events --namespace=<namespace> --field-selector involvedObject.name=<pod-name>

# Watch events
kubectl get events --namespace=<namespace> --watch

# Get events as YAML
kubectl get events --namespace=<namespace> -o yaml
```

### Useful Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# kubectl aliases
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deployments'
alias kgn='kubectl get nodes'
alias kge='kubectl get events'
alias kdp='kubectl describe pod'
alias kds='kubectl describe svc'
alias kdd='kubectl describe deployment'
alias kl='kubectl logs'
alias klf='kubectl logs -f'
alias kex='kubectl exec -it'
alias kpf='kubectl port-forward'

# Helm aliases
alias h='helm'
alias hl='helm list'
alias hh='helm history'
alias hs='helm status'
alias hhu='helm history'
alias hro='helm rollback'
```

---

## Additional Resources

### Useful Tools

```bash
# k9s - Terminal UI for Kubernetes
# Download from https://github.com/derailed/k9s/releases

# stern - Multi-pod log tailing
# Download from https://github.com/stern/stern/releases

# kubectx/kubens - Context/namespace switcher
git clone https://github.com/ahmetb/kubectx /opt/kubectx

# popeye - Cluster sanitizer
# Download from https://github.com/derailed/popeye/releases

# kubectl-neat - Clean kube output
kubectl krew install neat
```

### Monitoring and Observability

```bash
# Install Prometheus Operator
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Install Grafana
# Included with kube-prometheus-stack

# Access Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring

# Install Loki for log aggregation
helm install loki grafana/loki-stack --namespace=monitoring
```

---

**Last Updated:** 2025-01-23
**Document Version:** 1.0.0
