from collections import deque
import time

START_TIME = time.time()

metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "safety_triggers": 0,
    "retrieval_triggers": 0,
    "llm_errors": 0,
}

response_times = deque(maxlen=1000)


def record_request(latency: float, success: bool) -> None:
    """Record request latency and success status."""
    metrics["total_requests"] += 1
    if success:
        metrics["successful_requests"] += 1
    else:
        metrics["failed_requests"] += 1
    response_times.append(latency)


def record_safety_trigger() -> None:
    """Record a safety trigger."""
    metrics["safety_triggers"] += 1


def record_retrieval_trigger() -> None:
    """Record a retrieval trigger."""
    metrics["retrieval_triggers"] += 1


def record_llm_error() -> None:
    """Record an LLM error."""
    metrics["llm_errors"] += 1


def get_metrics() -> dict:
    """Get the current metrics snapshot."""
    uptime = time.time() - START_TIME
    recent_count = len(response_times)
    if recent_count > 0:
        avg_response_time = sum(response_times) / recent_count
    else:
        avg_response_time = 0.0

    return {
        "uptime_seconds": uptime,
        "total_requests": metrics["total_requests"],
        "successful_requests": metrics["successful_requests"],
        "failed_requests": metrics["failed_requests"],
        "safety_triggers": metrics["safety_triggers"],
        "retrieval_triggers": metrics["retrieval_triggers"],
        "llm_errors": metrics["llm_errors"],
        "average_response_time": avg_response_time,
        "recent_request_count": recent_count,
    }


def reset_metrics() -> None:
    """Reset the metrics counters, clear response times, and reset start time."""
    global START_TIME
    START_TIME = time.time()
    metrics["total_requests"] = 0
    metrics["successful_requests"] = 0
    metrics["failed_requests"] = 0
    metrics["safety_triggers"] = 0
    metrics["retrieval_triggers"] = 0
    metrics["llm_errors"] = 0
    response_times.clear()
