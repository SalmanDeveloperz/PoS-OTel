import os
import random
import time

from prometheus_client import Counter, Gauge, Histogram, start_http_server


RUNS = Counter(
    "pipeline_job_runs_total",
    "Total number of simulated pipeline jobs",
    ["status", "job_type"],
)
SUCCESSES = Counter(
    "pipeline_job_success_total",
    "Total number of successful pipeline jobs",
    ["job_type"],
)
FAILURES = Counter(
    "pipeline_job_failures_total",
    "Total number of failed pipeline jobs",
    ["job_type"],
)
DURATION = Histogram(
    "pipeline_job_duration_seconds",
    "Simulated pipeline job duration in seconds",
    ["job_type"],
    buckets=(0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)
IN_PROGRESS = Gauge(
    "pipeline_job_in_progress",
    "Number of jobs currently being simulated",
    ["job_type"],
)


def generate_job(job_type: str) -> None:
    IN_PROGRESS.labels(job_type=job_type).inc()
    try:
        duration = random.uniform(0.3, 5.0)
        if random.random() < 0.15:
            duration = random.uniform(10.0, 35.0)

        failed = random.random() < 0.2
        status = "failure" if failed else "success"

        DURATION.labels(job_type=job_type).observe(duration)
        RUNS.labels(status=status, job_type=job_type).inc()

        if failed:
            FAILURES.labels(job_type=job_type).inc()
        else:
            SUCCESSES.labels(job_type=job_type).inc()
    finally:
        IN_PROGRESS.labels(job_type=job_type).dec()


def main() -> None:
    port = int(os.environ.get("METRICS_PORT", "8000"))
    start_http_server(port)
    print(f"Pipeline simulator metrics on :{port}")

    job_types = ["build", "test", "deploy", "security-scan"]
    while True:
        job_type = random.choice(job_types)
        generate_job(job_type)
        time.sleep(random.uniform(0.5, 1.5))


if __name__ == "__main__":
    main()
