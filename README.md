# End-to-End OpenTelemetry + Prometheus + Grafana Stack

This repository provides a complete local observability setup for CI/CD pipelines:

- **Jenkins**: pipeline runner
- **OpenTelemetry Collector**: OTLP receiver, tail-sampling, span-to-metrics conversion
- **Jaeger**: traces UI
- **Prometheus**: metrics scraping + alert rules
- **Grafana**: pre-provisioned dashboards
- **Pipeline simulator**: generates live success/failure/slow-job metrics so dashboards are not empty

## What We Implemented

### 1) Full Docker Compose architecture

`docker-compose.yml` now includes:

- `jenkins`
- `jaeger`
- `otel-collector`
- `pipeline-simulator`
- `prometheus`
- `grafana`

Also added:

- persistent volumes for Prometheus and Grafana
- service startup dependencies
- exposed ports for UI and telemetry endpoints
- fixed port conflict by keeping Jaeger host port only on `16686` and using OTLP host ports on collector

### 2) OpenTelemetry Collector enhancements

`otel-collector-config.yaml` now includes:

- OTLP receiver (`4317` gRPC, `4318` HTTP)
- `tail_sampling` policies
  - keep errors
  - keep slow traces (>30s)
  - sample 20% of normal traces
- `spanmetrics` connector
- Prometheus exporter for metrics at `:8889`
- health check extension at `:13133`

### 3) Prometheus setup + alert rules

Added:

- `prometheus/prometheus.yml`
- `prometheus/alert_rules.yml`

Scrape jobs include:

- Prometheus self-metrics
- OTel Collector internal metrics
- OTel spanmetrics endpoint
- Pipeline simulator
- Jenkins `/prometheus` endpoint (when enabled)

Alert rules included:

- `PipelineFailureRateHigh`
- `PipelineSlowJobsDetected`
- `OTelCollectorDroppingSpans`

### 4) Grafana provisioning

Added:

- `grafana/provisioning/datasources/prometheus.yml`
- `grafana/provisioning/dashboards/dashboard.yml`
- `grafana/provisioning/dashboards/json/pipeline-observability.json`

Dashboard: **Pipeline Observability**

- Success rate (5m)
- Failure rate / sec
- Slow jobs / sec (>10s)
- Pipeline throughput
- p50/p95 duration by job type
- OTel collector ingestion

### 5) Pipeline simulator service

Added `pipeline-simulator` (Python + `prometheus_client`) that continuously emits:

- `pipeline_job_runs_total`
- `pipeline_job_success_total`
- `pipeline_job_failures_total`
- `pipeline_job_duration_seconds` histogram
- `pipeline_job_in_progress`

This gives immediate, realistic CI-like metrics for testing.

## Architecture

```text
Jenkins/Instrumented Apps (OTLP traces)
                   |
                   v
            OTel Collector
           /      |       \
          v       v        v
       Jaeger  spanmetrics  collector metrics
                  |
                  v
              Prometheus
                  |
                  v
               Grafana

Pipeline simulator ---> Prometheus ---> Grafana
```

## Quick Start

```bash
docker compose up -d --build
docker compose ps
```

## Access URLs

- Jenkins: [http://localhost:8080](http://localhost:8080)
- Jaeger: [http://localhost:16686](http://localhost:16686)
- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3000](http://localhost:3000)
  - Username: `admin`
  - Password: `admin`

## Beginner Test Flow (Naive-Friendly)

### Step 1: Check all containers are up

```bash
docker compose ps
```

Expected: all 6 services are `Up`.

### Step 2: Verify Prometheus targets

Open: [http://localhost:9090/targets](http://localhost:9090/targets)

Expected targets `UP`:

- `prometheus`
- `otel_collector_internal`
- `otel_spanmetrics`
- `pipeline_simulator`
- `jenkins` (optional, depends on Jenkins endpoint availability)

### Step 3: Verify metrics exist

In Prometheus Graph UI, run:

- `pipeline_job_runs_total`
- `pipeline_job_success_total`
- `pipeline_job_failures_total`
- `pipeline_job_duration_seconds_bucket`

Expected: non-empty data and increasing counters.

### Step 4: Verify dashboard

In Grafana, open **Observability > Pipeline Observability**.

Expected: panels update every 10s with live numbers and timeseries.

### Step 5: Verify traces in Jaeger

Open [http://localhost:16686](http://localhost:16686), select service, click **Find Traces**.

Expected:

- Jaeger internal traces always visible
- Jenkins traces visible after Jenkins OTel plugin is configured and jobs are run

## Jenkins OpenTelemetry Plugin Setup (Click-by-Click)

Use this to complete trace validation from Jenkins to Jaeger via collector.

1. Open Jenkins: [http://localhost:8080](http://localhost:8080)
2. Go to **Manage Jenkins > Plugins**
3. Install/verify **OpenTelemetry** plugin
4. Go to **Manage Jenkins > System**
5. Find **OpenTelemetry** section and set:
   - Endpoint: `http://otel-collector:4318` (if Jenkins uses Docker network route)
   - Protocol: OTLP/HTTP
   - Service name: `jenkins` (or your preferred name)
6. Save configuration
7. Run 2-3 pipelines (success + failure + slow)
8. Open Jaeger and verify service traces for Jenkins

If Jenkins cannot resolve `otel-collector`, use `http://localhost:4318`.

## Sample Jenkinsfile for Success/Failure/Slow Runs

Use this pipeline in Jenkins to generate realistic signal:

```groovy
pipeline {
  agent any
  stages {
    stage('Fast Success') {
      steps {
        echo 'Quick successful stage'
        sleep 2
      }
    }
    stage('Slow Stage') {
      steps {
        echo 'Simulate slow job stage'
        sleep 20
      }
    }
    stage('Optional Failure') {
      steps {
        script {
          if (env.BUILD_NUMBER.toInteger() % 3 == 0) {
            error('Simulated failure for observability testing')
          }
        }
      }
    }
  }
}
```

## How to Know It Is Correct

Your setup is correct when all of these are true:

- all services are running (`docker compose ps`)
- Prometheus targets are `UP`
- Prometheus queries return live data
- Grafana dashboard panels show values
- Jaeger shows traces for instrumented services
- collector logs show healthy startup without crash loops

## Useful Commands

```bash
# Start
docker compose up -d --build

# Stop
docker compose down

# Logs
docker compose logs -f
docker compose logs --tail=100 otel-collector
docker compose logs --tail=100 prometheus
docker compose logs --tail=100 grafana
```

## Notes About Common Logs

- `otlp alias is deprecated` in collector: warning only, non-blocking
- Grafana plugin auto-update permission errors (bundled plugin files): usually non-blocking for this stack
- Grafana 401 session token rotation warnings: expected during session refresh/re-login

## Validation Evidence (Screenshots)

These screenshots show live data from your running stack.

### 1) Prometheus metrics query view

![Prometheus Metrics Query](./screenshots/Screenshot%202026-04-26%20125439.png)

### 2) Grafana dashboard view

![Grafana Pipeline Dashboard](./screenshots/Screenshot%202026-04-26%20125509.png)

### 3) Jaeger trace view

![Jaeger Trace Search Results](./screenshots/Screenshot%202026-04-26%20125536.png)

## GSoC Project Alignment

This implementation aligns with the Jenkins GSoC idea:

**Project:** Use OpenTelemetry for Jenkins Jobs on `ci.jenkins.io`  
**Goal:** Enhance observability of Jenkins jobs using OpenTelemetry  
**Focus areas:** OpenTelemetry, observability, DevOps

What this repository demonstrates toward that goal:

- OpenTelemetry-based pipeline telemetry architecture
- Trace ingestion and tail-based sampling strategy
- Metrics pipeline with Prometheus
- Dashboarding and health visualization with Grafana
- Practical validation workflow for logs, metrics, traces, failures, and slow jobs

## Final Review Checklist

Current repository status is strong and presentation-ready. The setup already validates:

- working multi-service observability architecture
- live Prometheus metrics
- live Grafana dashboarding
- live Jaeger tracing UI
- documented runbook for reproducible testing

For production-like Jenkins validation, ensure Jenkins pipeline traces are sent to collector (`otel-collector:4318` or `localhost:4318`) and confirm Jenkins-specific traces in Jaeger.
