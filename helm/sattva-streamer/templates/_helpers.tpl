{{/*
Expand the name of the chart.
*/}}
{{- define "sattva-streamer.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "sattva-streamer.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "sattva-streamer.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "sattva-streamer.labels" -}}
helm.sh/chart: {{ include "sattva-streamer.chart" . }}
{{ include "sattva-streamer.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "sattva-streamer.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sattva-streamer.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "sattva-streamer.backend.labels" -}}
{{ include "sattva-streamer.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "sattva-streamer.backend.selectorLabels" -}}
{{ include "sattva-streamer.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "sattva-streamer.frontend.labels" -}}
{{ include "sattva-streamer.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "sattva-streamer.frontend.selectorLabels" -}}
{{ include "sattva-streamer.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Streamer labels
*/}}
{{- define "sattva-streamer.streamer.labels" -}}
{{ include "sattva-streamer.labels" . }}
app.kubernetes.io/component: streamer
{{- end }}

{{/*
Streamer selector labels
*/}}
{{- define "sattva-streamer.streamer.selectorLabels" -}}
{{ include "sattva-streamer.selectorLabels" . }}
app.kubernetes.io/component: streamer
{{- end }}

{{/*
Rust Transcoder labels
*/}}
{{- define "sattva-streamer.rustTranscoder.labels" -}}
{{ include "sattva-streamer.labels" . }}
app.kubernetes.io/component: rust-transcoder
{{- end }}

{{/*
Rust Transcoder selector labels
*/}}
{{- define "sattva-streamer.rustTranscoder.selectorLabels" -}}
{{ include "sattva-streamer.selectorLabels" . }}
app.kubernetes.io/component: rust-transcoder
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "sattva-streamer.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "sattva-streamer.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get the backend image
*/}}
{{- define "sattva-streamer.backend.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- if .Values.backend.image.registry }}
{{- $registry = .Values.backend.image.registry }}
{{- end }}
{{- printf "%s/%s:%s" $registry .Values.backend.image.repository .Values.backend.image.tag }}
{{- end }}

{{/*
Get the frontend image
*/}}
{{- define "sattva-streamer.frontend.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- if .Values.frontend.image.registry }}
{{- $registry = .Values.frontend.image.registry }}
{{- end }}
{{- printf "%s/%s:%s" $registry .Values.frontend.image.repository .Values.frontend.image.tag }}
{{- end }}

{{/*
Get the streamer image
*/}}
{{- define "sattva-streamer.streamer.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- if .Values.streamer.image.registry }}
{{- $registry = .Values.streamer.image.registry }}
{{- end }}
{{- printf "%s/%s:%s" $registry .Values.streamer.image.repository .Values.streamer.image.tag }}
{{- end }}

{{/*
Get the rust-transcoder image
*/}}
{{- define "sattva-streamer.rustTranscoder.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" }}
{{- if .Values.rustTranscoder.image.registry }}
{{- $registry = .Values.rustTranscoder.image.registry }}
{{- end }}
{{- printf "%s/%s:%s" $registry .Values.rustTranscoder.image.repository .Values.rustTranscoder.image.tag }}
{{- end }}

{{/*
Get the image pull secret if needed
*/}}
{{- define "sattva-streamer.imagePullSecrets" -}}
{{- if .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.global.imagePullSecrets }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Check if autoscaling is enabled for a component
*/}}
{{- define "sattva-streamer.autoscalingEnabled" -}}
{{- if .Values.autoscaling.enabled }}
{{- true }}
{{- else }}
{{- false }}
{{- end }}
{{- end }}

{{/*
Get the database connection URL
*/}}
{{- define "sattva-streamer.databaseURL" -}}
{{- if .Values.postgresql.enabled }}
postgresql://postgres:{{ .Values.postgresql.auth.postgresPassword }}@{{ .Release.Name }}-postgresql:5432/telegram_db
{{- else }}
{{- required "A valid database URL is required when PostgreSQL is disabled" .Values.backend.env.DATABASE_URL }}
{{- end }}
{{- end }}

{{/*
Get the Redis connection URL
*/}}
{{- define "sattva-streamer.redisURL" -}}
{{- if .Values.redis.enabled }}
redis://{{ .Release.Name }}-redis-master:6379
{{- else }}
{{- required "A valid Redis URL is required when Redis is disabled" .Values.backend.env.REDIS_URL }}
{{- end }}
{{- end }}

{{/*
Get the backend service name
*/}}
{{- define "sattva-streamer.backend.serviceName" -}}
{{- printf "%s-backend" (include "sattva-streamer.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Get the frontend service name
*/}}
{{- define "sattva-streamer.frontend.serviceName" -}}
{{- printf "%s-frontend" (include "sattva-streamer.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Get the frontend name
*/}}
{{- define "sattva-streamer.frontend.name" -}}
{{- printf "%s-frontend" (include "sattva-streamer.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Get the streamer service name
*/}}
{{- define "sattva-streamer.streamer.serviceName" -}}
{{- printf "%s-streamer" (include "sattva-streamer.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Get the rust-transcoder service name
*/}}
{{- define "sattva-streamer.rustTranscoder.serviceName" -}}
{{- printf "%s-rust-transcoder" (include "sattva-streamer.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Helper to check if HPA should be created
*/}}
{{- define "sattva-streamer.canCreateHPA" -}}
{{- if and .Capabilities.APIVersions.Has "autoscaling/v2" .Values.backend.autoscaling.enabled }}
{{- true }}
{{- else }}
{{- false }}
{{- end }}
{{- end }}

{{/*
Helper to check if PDB should be created
*/}}
{{- define "sattva-streamer.canCreatePDB" -}}
{{- if and .Capabilities.APIVersions.Has "policy/v1" .Values.podDisruptionBudget.backend.enabled }}
{{- true }}
{{- else }}
{{- false }}
{{- end }}
{{- end }}

{{/*
Helper to check if NetworkPolicy should be created
*/}}
{{- define "sattva-streamer.canCreateNetworkPolicy" -}}
{{- if and .Capabilities.APIVersions.Has "networking.k8s.io/v1" .Values.networkPolicy.enabled }}
{{- true }}
{{- else }}
{{- false }}
{{- end }}
{{- end }}

{{/*
Helper to check if ServiceMonitor should be created
*/}}
{{- define "sattva-streamer.canCreateServiceMonitor" -}}
{{- if and .Capabilities.APIVersions.Has "monitoring.coreos.com/v1" .Values.monitoring.serviceMonitor.enabled }}
{{- true }}
{{- else }}
{{- false }}
{{- end }}
{{- end }}

{{/*
Helper to check if Ingress should be created
*/}}
{{- define "sattva-streamer.canCreateIngress" -}}
{{- if and .Capabilities.APIVersions.Has "networking.k8s.io/v1" .Values.ingress.enabled }}
{{- true }}
{{- else }}
{{- false }}
{{- end }}
{{- end }}

{{/*
Helper to build environment variables list
*/}}
{{- define "sattva-streamer.envVars" -}}
{{- range $key, $value := .env }}
- name: {{ $key }}
  value: {{ tpl $value $ | quote }}
{{- end }}
{{- end }}

{{/*
Helper to build secret environment variables list
*/}}
{{- define "sattva-streamer.secretEnvVars" -}}
{{- range $key, $secret := .secretEnv }}
- name: {{ $key }}
  valueFrom:
    secretKeyRef:
      name: {{ printf "%s-secrets" $.Release.Name }}
      key: {{ $secret }}
{{- end }}
{{- end }}

{{/*
Convert value to string
*/}}
{{- define "sattva-streamer.toString" -}}
{{- if kindIs "string" . }}
{{- . }}
{{- else if kindIs "int" . }}
{{- printf "%d" . }}
{{- else if kindIs "float64" . }}
{{- printf "%f" . }}
{{- else if kindIs "bool" . }}
{{- printf "%t" . }}
{{- else }}
{{- printf "%v" . }}
{{- end }}
{{- end }}
