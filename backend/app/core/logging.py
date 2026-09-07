import json
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

# Context variables to track request scope metadata
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")

class JSONFormatter(logging.Formatter):
    """Custom formatter to emit structured logs in JSON format."""
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get()
        }
        
        # Inject standard record attributes if present in extra
        for attr in ["endpoint", "method", "status_code", "latency_ms", 
                     "incident_id", "service_name", "model_name", "model_version"]:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)
                
        return json.dumps(log_data)

def setup_logging():
    """Configure system logging to output JSON."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)

# Helper function to log intelligence inferences
logger = logging.getLogger("oil-spill")

def log_inference(
    service_name: str,
    model_name: str = "ml-model",
    model_version: str = "v1.0",
    analysis_id: str = "",
    incident_id: str = "",
    latency_ms: float = 0,
    status_code: int = 200,
    message: str = "Inference completed"
):
    """Log structured intelligence service metadata."""
    logger.info(
        message,
        extra={
            "service_name": service_name,
            "model_name": model_name,
            "model_version": model_version,
            "analysis_id": analysis_id,
            "incident_id": incident_id,
            "latency_ms": latency_ms,
            "status_code": status_code
        }
    )
