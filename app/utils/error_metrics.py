"""
Error metrics and monitoring for OCR operations.

Provides comprehensive error tracking, metrics collection, alerting,
and monitoring capabilities for robust error analysis.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
from pathlib import Path

from app.core.ocr_errors import OCRError, OCRErrorCode
from app.utils.error_sanitizer import ErrorSeverity

logger = logging.getLogger(__name__)

class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(str, Enum):
    """Types of metrics we track."""
    ERROR_COUNT = "error_count"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    LATENCY = "latency"
    THROUGHPUT = "throughput"

@dataclass
class ErrorMetric:
    """Individual error metric data."""
    timestamp: float
    error_code: str
    error_message: str
    operation: str
    correlation_id: str
    severity: str
    recoverable: bool
    processing_time_ms: float = 0
    file_size_mb: float = 0
    user_info: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    metric_type: MetricType
    threshold_value: float
    time_window_seconds: int
    alert_level: AlertLevel
    description: str
    enabled: bool = True

@dataclass
class MetricsSummary:
    """Summary of metrics for a time period."""
    start_time: float
    end_time: float
    total_requests: int
    total_errors: int
    error_rate: float
    success_rate: float
    avg_processing_time_ms: float
    errors_by_code: Dict[str, int]
    errors_by_operation: Dict[str, int]
    errors_by_severity: Dict[str, int]
    top_error_messages: List[Tuple[str, int]]

class ErrorMetricsCollector:
    """Collects and analyzes error metrics."""
    
    def __init__(self, max_metrics_memory: int = 10000):
        self.max_metrics_memory = max_metrics_memory
        self.metrics: deque = deque(maxlen=max_metrics_memory)
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.lock = threading.RLock()
        
        # Alert thresholds
        self.alert_thresholds = [
            AlertThreshold(
                MetricType.ERROR_RATE,
                0.1,  # 10% error rate
                300,  # 5 minutes
                AlertLevel.WARNING,
                "Error rate exceeded 10% in 5 minutes"
            ),
            AlertThreshold(
                MetricType.ERROR_RATE,
                0.25,  # 25% error rate
                300,  # 5 minutes
                AlertLevel.CRITICAL,
                "Error rate exceeded 25% in 5 minutes"
            ),
            AlertThreshold(
                MetricType.ERROR_COUNT,
                50,  # 50 errors
                600,  # 10 minutes
                AlertLevel.ERROR,
                "More than 50 errors in 10 minutes"
            ),
            AlertThreshold(
                MetricType.LATENCY,
                30000,  # 30 seconds
                300,  # 5 minutes
                AlertLevel.WARNING,
                "Average processing time exceeded 30 seconds"
            )
        ]
        
        # Alert history to prevent spam
        self.alert_history: Dict[str, float] = {}
        self.alert_cooldown = 1800  # 30 minutes between same alerts
    
    def record_error(
        self,
        error: OCRError,
        operation: str,
        processing_time_ms: float = 0,
        file_size_mb: float = 0,
        user_info: Optional[Dict[str, Any]] = None
    ):
        """Record an error metric."""
        with self.lock:
            metric = ErrorMetric(
                timestamp=time.time(),
                error_code=error.error_code.value,
                error_message=error.message,
                operation=operation,
                correlation_id=error.context.correlation_id if error.context else "unknown",
                severity=ErrorSeverity.HIGH.value,  # Default severity
                recoverable=error.recoverable,
                processing_time_ms=processing_time_ms,
                file_size_mb=file_size_mb,
                user_info=user_info,
                context=error.context.to_dict() if error.context else None
            )
            
            self.metrics.append(metric)
            self.error_counts[error.error_code.value] += 1
            
            # Check alert thresholds
            self._check_alert_thresholds()
    
    def record_success(
        self,
        operation: str,
        processing_time_ms: float,
        file_size_mb: float = 0,
        user_info: Optional[Dict[str, Any]] = None
    ):
        """Record a successful operation."""
        with self.lock:
            self.request_counts[operation] += 1
            
            # Store success metrics for analysis
            success_metric = {
                "timestamp": time.time(),
                "operation": operation,
                "processing_time_ms": processing_time_ms,
                "file_size_mb": file_size_mb,
                "success": True,
                "user_info": user_info
            }
            
            # Add to metrics as a success entry
            self.metrics.append(success_metric)
    
    def get_metrics_summary(self, time_window_seconds: int = 3600) -> MetricsSummary:
        """Get metrics summary for a time window."""
        with self.lock:
            current_time = time.time()
            start_time = current_time - time_window_seconds
            
            # Filter metrics within time window
            recent_metrics = [
                m for m in self.metrics
                if isinstance(m, (ErrorMetric, dict)) and 
                (m.timestamp if isinstance(m, ErrorMetric) else m.get('timestamp', 0)) >= start_time
            ]
            
            if not recent_metrics:
                return MetricsSummary(
                    start_time=start_time,
                    end_time=current_time,
                    total_requests=0,
                    total_errors=0,
                    error_rate=0.0,
                    success_rate=1.0,
                    avg_processing_time_ms=0.0,
                    errors_by_code={},
                    errors_by_operation={},
                    errors_by_severity={},
                    top_error_messages=[]
                )
            
            # Separate errors and successes
            errors = [m for m in recent_metrics if isinstance(m, ErrorMetric)]
            successes = [m for m in recent_metrics if isinstance(m, dict) and m.get('success', False)]
            
            total_requests = len(recent_metrics)
            total_errors = len(errors)
            
            error_rate = total_errors / total_requests if total_requests > 0 else 0.0
            success_rate = 1.0 - error_rate
            
            # Calculate average processing time
            processing_times = []
            for metric in recent_metrics:
                if isinstance(metric, ErrorMetric):
                    processing_times.append(metric.processing_time_ms)
                elif isinstance(metric, dict):
                    processing_times.append(metric.get('processing_time_ms', 0))
            
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
            
            # Group errors by various dimensions
            errors_by_code = defaultdict(int)
            errors_by_operation = defaultdict(int)
            errors_by_severity = defaultdict(int)
            error_messages = defaultdict(int)
            
            for error in errors:
                errors_by_code[error.error_code] += 1
                errors_by_operation[error.operation] += 1
                errors_by_severity[error.severity] += 1
                error_messages[error.error_message] += 1
            
            # Get top error messages
            top_error_messages = sorted(
                error_messages.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return MetricsSummary(
                start_time=start_time,
                end_time=current_time,
                total_requests=total_requests,
                total_errors=total_errors,
                error_rate=error_rate,
                success_rate=success_rate,
                avg_processing_time_ms=avg_processing_time,
                errors_by_code=dict(errors_by_code),
                errors_by_operation=dict(errors_by_operation),
                errors_by_severity=dict(errors_by_severity),
                top_error_messages=top_error_messages
            )
    
    def get_error_trends(self, time_window_seconds: int = 3600, bucket_size_seconds: int = 300) -> Dict[str, Any]:
        """Get error trends over time with buckets."""
        with self.lock:
            current_time = time.time()
            start_time = current_time - time_window_seconds
            
            # Create time buckets
            num_buckets = time_window_seconds // bucket_size_seconds
            buckets = []
            
            for i in range(num_buckets):
                bucket_start = start_time + (i * bucket_size_seconds)
                bucket_end = bucket_start + bucket_size_seconds
                
                bucket_metrics = [
                    m for m in self.metrics
                    if isinstance(m, (ErrorMetric, dict)) and
                    bucket_start <= (m.timestamp if isinstance(m, ErrorMetric) else m.get('timestamp', 0)) < bucket_end
                ]
                
                bucket_errors = [m for m in bucket_metrics if isinstance(m, ErrorMetric)]
                total_requests = len(bucket_metrics)
                total_errors = len(bucket_errors)
                
                error_rate = total_errors / total_requests if total_requests > 0 else 0.0
                
                buckets.append({
                    "timestamp": bucket_start,
                    "total_requests": total_requests,
                    "total_errors": total_errors,
                    "error_rate": error_rate,
                    "errors_by_code": {
                        code: sum(1 for e in bucket_errors if e.error_code == code)
                        for code in set(e.error_code for e in bucket_errors)
                    } if bucket_errors else {}
                })
            
            return {
                "time_window_seconds": time_window_seconds,
                "bucket_size_seconds": bucket_size_seconds,
                "buckets": buckets,
                "trends": self._calculate_trends(buckets)
            }
    
    def _calculate_trends(self, buckets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend analysis from buckets."""
        if len(buckets) < 2:
            return {"trend": "insufficient_data"}
        
        error_rates = [bucket["error_rate"] for bucket in buckets]
        request_counts = [bucket["total_requests"] for bucket in buckets]
        
        # Simple trend calculation
        recent_half = error_rates[len(error_rates)//2:]
        early_half = error_rates[:len(error_rates)//2]
        
        recent_avg = sum(recent_half) / len(recent_half) if recent_half else 0
        early_avg = sum(early_half) / len(early_half) if early_half else 0
        
        if recent_avg > early_avg * 1.5:
            trend = "increasing"
        elif recent_avg < early_avg * 0.5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "recent_avg_error_rate": recent_avg,
            "early_avg_error_rate": early_avg,
            "avg_requests_per_bucket": sum(request_counts) / len(request_counts)
        }
    
    def _check_alert_thresholds(self):
        """Check if any alert thresholds are exceeded."""
        current_time = time.time()
        
        for threshold in self.alert_thresholds:
            if not threshold.enabled:
                continue
            
            # Check cooldown
            alert_key = f"{threshold.metric_type.value}_{threshold.threshold_value}"
            if alert_key in self.alert_history:
                if current_time - self.alert_history[alert_key] < self.alert_cooldown:
                    continue
            
            # Calculate metric value
            metric_value = self._calculate_metric_value(threshold.metric_type, threshold.time_window_seconds)
            
            if metric_value >= threshold.threshold_value:
                self._trigger_alert(threshold, metric_value)
                self.alert_history[alert_key] = current_time
    
    def _calculate_metric_value(self, metric_type: MetricType, time_window_seconds: int) -> float:
        """Calculate metric value for threshold checking."""
        summary = self.get_metrics_summary(time_window_seconds)
        
        if metric_type == MetricType.ERROR_RATE:
            return summary.error_rate
        elif metric_type == MetricType.ERROR_COUNT:
            return summary.total_errors
        elif metric_type == MetricType.SUCCESS_RATE:
            return summary.success_rate
        elif metric_type == MetricType.LATENCY:
            return summary.avg_processing_time_ms
        elif metric_type == MetricType.THROUGHPUT:
            return summary.total_requests / (time_window_seconds / 60)  # requests per minute
        
        return 0.0
    
    def _trigger_alert(self, threshold: AlertThreshold, current_value: float):
        """Trigger an alert when threshold is exceeded."""
        alert_data = {
            "timestamp": time.time(),
            "alert_level": threshold.alert_level.value,
            "metric_type": threshold.metric_type.value,
            "threshold_value": threshold.threshold_value,
            "current_value": current_value,
            "description": threshold.description,
            "time_window_seconds": threshold.time_window_seconds
        }
        
        logger.error(
            f"ALERT [{threshold.alert_level.value.upper()}]: {threshold.description}",
            extra={
                "alert_data": alert_data,
                "metric_type": threshold.metric_type.value,
                "current_value": current_value,
                "threshold": threshold.threshold_value
            }
        )
        
        # Here you could integrate with external alerting systems
        # self._send_external_alert(alert_data)
    
    def export_metrics(self, filepath: str, time_window_seconds: int = 3600):
        """Export metrics to a file."""
        summary = self.get_metrics_summary(time_window_seconds)
        trends = self.get_error_trends(time_window_seconds)
        
        export_data = {
            "export_timestamp": time.time(),
            "time_window_seconds": time_window_seconds,
            "summary": asdict(summary),
            "trends": trends,
            "alert_thresholds": [asdict(t) for t in self.alert_thresholds],
            "recent_metrics": [
                asdict(m) if isinstance(m, ErrorMetric) else m
                for m in list(self.metrics)[-100:]  # Last 100 metrics
            ]
        }
        
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Metrics exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {str(e)}")
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall health score based on metrics."""
        summary = self.get_metrics_summary(3600)  # Last hour
        
        # Base score calculation
        error_rate_score = max(0, 100 - (summary.error_rate * 500))  # Heavy penalty for errors
        latency_score = max(0, 100 - (summary.avg_processing_time_ms / 100))  # Penalty for slow processing
        
        # Volume score (penalize very low volume as it might indicate issues)
        volume_score = min(100, summary.total_requests * 2) if summary.total_requests > 0 else 0
        
        # Weighted average
        health_score = (error_rate_score * 0.5 + latency_score * 0.3 + volume_score * 0.2)
        
        # Determine health status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 50:
            status = "fair"
        elif health_score >= 25:
            status = "poor"
        else:
            status = "critical"
        
        return {
            "health_score": round(health_score, 1),
            "status": status,
            "components": {
                "error_rate_score": round(error_rate_score, 1),
                "latency_score": round(latency_score, 1),
                "volume_score": round(volume_score, 1)
            },
            "summary": summary,
            "recommendations": self._generate_health_recommendations(summary, health_score)
        }
    
    def _generate_health_recommendations(self, summary: MetricsSummary, health_score: float) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if summary.error_rate > 0.1:
            recommendations.append("High error rate detected - review error logs and fix common issues")
        
        if summary.avg_processing_time_ms > 15000:
            recommendations.append("Slow processing times - consider optimizing document processing")
        
        if summary.total_requests < 10:
            recommendations.append("Low request volume - verify service availability and monitoring")
        
        if health_score < 50:
            recommendations.append("Critical health score - immediate investigation required")
        
        # Error-specific recommendations
        if "API_AUTHENTICATION_FAILED" in summary.errors_by_code:
            recommendations.append("Authentication failures detected - verify API key configuration")
        
        if "FILE_TOO_LARGE" in summary.errors_by_code:
            recommendations.append("File size errors - consider implementing better size validation")
        
        if not recommendations:
            recommendations.append("System operating normally - continue monitoring")
        
        return recommendations

# Global metrics collector instance
metrics_collector = ErrorMetricsCollector()

def record_error_metric(
    error: OCRError,
    operation: str,
    processing_time_ms: float = 0,
    file_size_mb: float = 0,
    user_info: Optional[Dict[str, Any]] = None
):
    """Convenience function to record error metrics."""
    metrics_collector.record_error(error, operation, processing_time_ms, file_size_mb, user_info)

def record_success_metric(
    operation: str,
    processing_time_ms: float,
    file_size_mb: float = 0,
    user_info: Optional[Dict[str, Any]] = None
):
    """Convenience function to record success metrics."""
    metrics_collector.record_success(operation, processing_time_ms, file_size_mb, user_info)

def get_metrics_summary(time_window_seconds: int = 3600) -> MetricsSummary:
    """Convenience function to get metrics summary."""
    return metrics_collector.get_metrics_summary(time_window_seconds)

def get_health_score() -> Dict[str, Any]:
    """Convenience function to get health score."""
    return metrics_collector.get_health_score()
