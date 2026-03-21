package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"
)

type ServiceInfo struct {
	Service   Service    `json:"service"`
	System    System     `json:"system"`
	Runtime   Runtime    `json:"runtime"`
	Request   Request    `json:"request"`
	Endpoints []Endpoint `json:"endpoints"`
}

type Service struct {
	Name        string `json:"name"`
	Version     string `json:"version"`
	Description string `json:"description"`
	Framework   string `json:"framework"`
}

type System struct {
	Hostname        string `json:"hostname"`
	Platform        string `json:"platform"`
	PlatformVersion string `json:"platform_version"`
	Architecture    string `json:"architecture"`
	CPUCount        int    `json:"cpu_count"`
	GoVersion       string `json:"python_version"`
}

type Runtime struct {
	UptimeSeconds int    `json:"uptime_seconds"`
	UptimeHuman   string `json:"uptime_human"`
	CurrentTime   string `json:"current_time"`
	Timezone      string `json:"timezone"`
}

type Request struct {
	ClientIP  string `json:"client_ip"`
	UserAgent string `json:"user_agent"`
	Method    string `json:"method"`
	Path      string `json:"path"`
}

type Endpoint struct {
	Path        string `json:"path"`
	Method      string `json:"method"`
	Description string `json:"description"`
}

type Health struct {
	Status        string `json:"status"`
	Timestamp     string `json:"timestamp"`
	UptimeSeconds int    `json:"uptime_seconds"`
}

type statusRecorder struct {
	http.ResponseWriter
	statusCode int
}

var startTime = time.Now().UTC()

func nowISO() string {
	return time.Now().UTC().Format(time.RFC3339)
}

func nowISONanos() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}

func uptime() (int, string) {
	seconds := int(time.Since(startTime).Seconds())
	hours := seconds / 3600
	minutes := (seconds % 3600) / 60
	return seconds, strconv.Itoa(hours) + " hours, " + strconv.Itoa(minutes) + " minutes"
}

func systemInfo() System {
	hostname, _ := os.Hostname()
	return System{
		Hostname:        hostname,
		Platform:        runtime.GOOS,
		PlatformVersion: platformVersion(),
		Architecture:    runtime.GOARCH,
		CPUCount:        runtime.NumCPU(),
		GoVersion:       runtime.Version(),
	}
}

func platformVersion() string {
	if runtime.GOOS == "linux" {
		file, err := os.Open("/etc/os-release")
		if err == nil {
			defer file.Close()
			scanner := bufio.NewScanner(file)
			for scanner.Scan() {
				line := scanner.Text()
				if strings.HasPrefix(line, "PRETTY_NAME=") {
					value := strings.TrimPrefix(line, "PRETTY_NAME=")
					return strings.Trim(value, "\"")
				}
			}
		}
	}

	return runtime.GOOS
}

func clientIP(r *http.Request) string {
	ip, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return ip
}

func (sr *statusRecorder) WriteHeader(statusCode int) {
	sr.statusCode = statusCode
	sr.ResponseWriter.WriteHeader(statusCode)
}

func writeJSONLog(level string, message string, fields map[string]any) {
	entry := map[string]any{
		"timestamp": nowISONanos(),
		"level":     level,
		"logger":    "devops-info-service-go",
		"message":   message,
	}

	for key, value := range fields {
		entry[key] = value
	}

	if encoded, err := json.Marshal(entry); err == nil {
		fmt.Println(string(encoded))
		return
	}

	fmt.Printf("{\"timestamp\":\"%s\",\"level\":\"ERROR\",\"logger\":\"devops-info-service-go\",\"message\":\"failed to encode log entry\"}\n", nowISONanos())
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		recorder := &statusRecorder{
			ResponseWriter: w,
			statusCode:     http.StatusOK,
		}

		next.ServeHTTP(recorder, r)

		level := "INFO"
		if recorder.statusCode >= http.StatusInternalServerError {
			level = "ERROR"
		} else if recorder.statusCode >= http.StatusBadRequest {
			level = "WARN"
		}

		writeJSONLog(level, "HTTP request processed", map[string]any{
			"event":       "http_request",
			"method":      r.Method,
			"path":        r.URL.Path,
			"status_code": recorder.statusCode,
			"client_ip":   clientIP(r),
			"user_agent":  r.UserAgent(),
			"duration_ms": float64(time.Since(started).Microseconds()) / 1000.0,
		})
	})
}

func mainHandler(w http.ResponseWriter, r *http.Request) {
	secs, human := uptime()
	info := ServiceInfo{
		Service: Service{
			Name:        "devops-info-service",
			Version:     "1.0.0",
			Description: "DevOps course info service",
			Framework:   "Go net/http",
		},
		System:  systemInfo(),
		Runtime: Runtime{UptimeSeconds: secs, UptimeHuman: human, CurrentTime: nowISO(), Timezone: "UTC"},
		Request: Request{ClientIP: clientIP(r), UserAgent: r.UserAgent(), Method: r.Method, Path: r.URL.Path},
		Endpoints: []Endpoint{
			{Path: "/", Method: "GET", Description: "Service information"},
			{Path: "/health", Method: "GET", Description: "Health check"},
		},
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(info)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	secs, _ := uptime()
	health := Health{Status: "healthy", Timestamp: nowISO(), UptimeSeconds: secs}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(health)
}

func notFoundHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNotFound)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": "Not Found", "message": "Endpoint does not exist"})
}

func main() {
	host := os.Getenv("HOST")
	if host == "" {
		host = "0.0.0.0"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			notFoundHandler(w, r)
			return
		}
		mainHandler(w, r)
	})
	mux.HandleFunc("/health", healthHandler)

	addr := host + ":" + port
	writeJSONLog("INFO", "Starting server", map[string]any{
		"event": "startup",
		"host":  host,
		"port":  port,
	})
	if err := http.ListenAndServe(addr, loggingMiddleware(mux)); err != nil {
		writeJSONLog("ERROR", "Server exited", map[string]any{
			"event": "shutdown",
			"error": err.Error(),
		})
		os.Exit(1)
	}
}
