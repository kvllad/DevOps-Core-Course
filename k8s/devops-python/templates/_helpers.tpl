{{/*
Resolve Secret name. Uses provided override when set.
*/}}
{{- define "devops-python.secretName" -}}
{{- if .Values.secrets.name -}}
{{- .Values.secrets.name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-app-credentials" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Resolve file ConfigMap name. Uses provided override when set.
*/}}
{{- define "devops-python.configMapName" -}}
{{- if .Values.configMaps.file.name -}}
{{- .Values.configMaps.file.name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-config" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Resolve environment ConfigMap name. Uses provided override when set.
*/}}
{{- define "devops-python.envConfigMapName" -}}
{{- if .Values.configMaps.env.name -}}
{{- .Values.configMaps.env.name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-env" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Resolve PVC name. Uses provided override when set.
*/}}
{{- define "devops-python.pvcName" -}}
{{- if .Values.persistence.name -}}
{{- .Values.persistence.name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-data" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Resolve preview Service name for blue-green rollouts.
*/}}
{{- define "devops-python.previewServiceName" -}}
{{- printf "%s-preview" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Resolve AnalysisTemplate name for canary verification.
*/}}
{{- define "devops-python.analysisTemplateName" -}}
{{- printf "%s-canary-health" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Resolve headless Service name for StatefulSet DNS.
*/}}
{{- define "devops-python.headlessServiceName" -}}
{{- printf "%s-headless" (include "common.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Resolve ServiceAccount name. Uses provided override when set.
*/}}
{{- define "devops-python.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name | trunc 63 | trimSuffix "-" -}}
{{- else if .Values.serviceAccount.create -}}
{{- include "common.fullname" . -}}
{{- else -}}
default
{{- end -}}
{{- end -}}

{{/*
Pod annotations shared by Deployment and Rollout templates.
*/}}
{{- define "devops-python.podAnnotations" -}}
{{- if or .Values.vault.enabled .Values.podAnnotations .Values.configMaps.file.enabled .Values.configMaps.env.enabled }}
annotations:
  {{- if or .Values.configMaps.file.enabled .Values.configMaps.env.enabled }}
  checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
  {{- end }}
  {{- if .Values.vault.enabled }}
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: {{ .Values.vault.role | quote }}
  vault.hashicorp.com/agent-inject-secret-{{ .Values.vault.renderFile }}: {{ .Values.vault.secretPath | quote }}
  vault.hashicorp.com/agent-inject-template-{{ .Values.vault.renderFile }}: |
    {{- include "devops-python.vaultEnvTemplate" . | nindent 4 }}
  vault.hashicorp.com/agent-inject-command-{{ .Values.vault.renderFile }}: {{ .Values.vault.command | quote }}
  {{- end }}
  {{- with .Values.podAnnotations }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
{{- end }}
{{- end -}}

{{/*
Common environment variables for the container.
*/}}
{{- define "devops-python.envVars" -}}
- name: PORT
  value: {{ .Values.containerPort | quote }}
{{- range $name, $value := .Values.env }}
- name: {{ $name }}
  value: {{ $value | quote }}
{{- end }}
{{- end -}}

{{/*
Shared volume mounts for app workloads.
*/}}
{{- define "devops-python.volumeMounts" -}}
{{- if or .Values.configMaps.file.enabled .Values.persistence.enabled }}
volumeMounts:
  {{- if .Values.configMaps.file.enabled }}
  - name: config-volume
    mountPath: {{ .Values.configMaps.file.mountPath }}
    readOnly: true
  {{- end }}
  {{- if .Values.persistence.enabled }}
  - name: data-volume
    mountPath: {{ .Values.persistence.mountPath }}
  {{- end }}
  {{- if .Values.initContainers.enabled }}
  - name: init-shared
    mountPath: {{ .Values.initContainers.sharedVolume.mountPath }}
  {{- end }}
{{- end }}
{{- end -}}

{{/*
Shared volumes for non-StatefulSet workloads.
*/}}
{{- define "devops-python.workloadVolumes" -}}
{{- if or .Values.configMaps.file.enabled .Values.persistence.enabled }}
volumes:
  {{- if .Values.configMaps.file.enabled }}
  - name: config-volume
    configMap:
      name: {{ include "devops-python.configMapName" . }}
  {{- end }}
  {{- if .Values.persistence.enabled }}
  - name: data-volume
    persistentVolumeClaim:
      claimName: {{ include "devops-python.pvcName" . }}
  {{- end }}
  {{- if .Values.initContainers.enabled }}
  - name: init-shared
    emptyDir: {}
  {{- end }}
{{- end }}
{{- end -}}

{{/*
Init containers for setup and dependency waiting.
*/}}
{{- define "devops-python.initContainers" -}}
{{- if .Values.initContainers.enabled }}
initContainers:
  {{- if .Values.initContainers.download.enabled }}
  - name: init-download
    image: "{{ .Values.initContainers.download.image.repository }}:{{ .Values.initContainers.download.image.tag }}"
    imagePullPolicy: {{ .Values.initContainers.download.image.pullPolicy }}
    command:
      - sh
      - -c
      - wget -O {{ .Values.initContainers.download.outputPath }} {{ .Values.initContainers.download.url }}
    volumeMounts:
      - name: init-shared
        mountPath: {{ .Values.initContainers.sharedVolume.mountPath }}
  {{- end }}
  {{- if .Values.initContainers.waitForService.enabled }}
  - name: wait-for-service
    image: "{{ .Values.initContainers.waitForService.image.repository }}:{{ .Values.initContainers.waitForService.image.tag }}"
    imagePullPolicy: {{ .Values.initContainers.waitForService.image.pullPolicy }}
    command:
      - sh
      - -c
      - until nslookup {{ .Values.initContainers.waitForService.host }}; do sleep {{ .Values.initContainers.waitForService.intervalSeconds }}; done
  {{- end }}
{{- end }}
{{- end -}}

{{/*
Vault Agent template that renders a .env-like file.
*/}}
{{- define "devops-python.vaultEnvTemplate" -}}
{{ "{{- with secret \"" }}{{ .Values.vault.secretPath }}{{ "\" -}}" }}
APP_USERNAME={{ "{{ .Data.data.username }}" }}
APP_PASSWORD={{ "{{ .Data.data.password }}" }}
APP_API_KEY={{ "{{ .Data.data.api_key }}" }}
{{ "{{- end }}" }}
{{- end -}}
