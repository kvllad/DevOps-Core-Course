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
Common environment variables for the container.
*/}}
{{- define "devops-python.envVars" -}}
- name: PORT
  value: {{ .Values.containerPort | quote }}
- name: APP_ENV
  value: {{ .Values.app.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.app.logLevel | quote }}
{{- range $name, $value := .Values.env }}
- name: {{ $name }}
  value: {{ $value | quote }}
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
