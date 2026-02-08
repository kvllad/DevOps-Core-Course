# syntax=docker/dockerfile:1
FROM golang:1.22.5-alpine AS builder

WORKDIR /src

COPY go.mod ./
RUN go mod download

COPY . ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w" -o /out/devops-info-service ./main.go

FROM alpine:3.20

RUN addgroup -S app && adduser -S -G app app

WORKDIR /app
COPY --from=builder /out/devops-info-service /app/devops-info-service

USER app
EXPOSE 8080

CMD ["/app/devops-info-service"]
