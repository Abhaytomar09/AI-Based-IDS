"""
FastAPI inference service
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import uvicorn
import json
from datetime import datetime

from src.inference import get_inference_engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered IDS API",
    description="Real-time intrusion detection system with ML/DL hybrid approach",
    version="1.0.0"
)

# Request/Response models
class FlowData(BaseModel):
    """Network flow data."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str = "TCP"
    duration: float = 0.0
    src_bytes: int = 0
    dst_bytes: int = 0
    num_packets: int = 0
    flags: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.5",
                "src_port": 12345,
                "dst_port": 80,
                "protocol": "TCP",
                "duration": 10.5,
                "src_bytes": 1024,
                "dst_bytes": 512,
                "num_packets": 50
            }
        }


class PredictionResponse(BaseModel):
    """Prediction response."""
    timestamp: str
    flow_id: str
    models: Dict[str, Any]
    alert: Optional[Dict[str, Any]] = None


class BatchRequest(BaseModel):
    """Batch prediction request."""
    flows: List[FlowData]


class BatchResponse(BaseModel):
    """Batch prediction response."""
    predictions: List[PredictionResponse]
    summary: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    models_loaded: Dict[str, bool]
    timestamp: str


# Initialize inference engine
engine = None


@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    global engine
    logger.info("Starting up API server...")
    
    try:
        engine = get_inference_engine()
        logger.info("Inference engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize inference engine: {e}")
        raise


@app.get("/", tags=["Info"])
async def root():
    """API root endpoint."""
    return {
        "name": "AI-Powered IDS API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    if engine is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    models_loaded = {
        'xgboost': engine.xgb_classifier.model is not None,
        'random_forest': engine.rf_classifier.model is not None,
        'autoencoder': engine.ae_detector.model is not None,
        'isolation_forest': engine.if_detector.model is not None,
        'scaler': engine.scaler is not None
    }
    
    return HealthResponse(
        status="healthy" if any(models_loaded.values()) else "degraded",
        models_loaded=models_loaded,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Predictions"])
async def predict(flow: FlowData):
    """
    Predict whether a network flow is malicious.
    
    Returns:
    - **alert**: Triggered if malicious activity detected
    - **models**: Individual model predictions
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        data = flow.dict()
        result = engine.predict(data)
        return PredictionResponse(**result)
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch", response_model=BatchResponse, tags=["Predictions"])
async def batch_predict(request: BatchRequest):
    """
    Batch prediction on multiple flows.
    
    Returns:
    - **predictions**: List of predictions
    - **summary**: Aggregate statistics
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        predictions = []
        alert_count = 0
        
        for flow in request.flows:
            data = flow.dict()
            result = engine.predict(data)
            predictions.append(PredictionResponse(**result))
            
            if result.get('alert'):
                alert_count += 1
        
        summary = {
            'total_flows': len(predictions),
            'alerts_triggered': alert_count,
            'alert_rate': alert_count / len(predictions) if predictions else 0.0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return BatchResponse(predictions=predictions, summary=summary)
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/explain/{flow_id}", tags=["Explainability"])
async def explain_prediction(flow_id: str):
    """
    Get explainability information for a prediction.
    
    Returns:
    - **feature_importance**: Top contributing features
    - **model_confidence**: Confidence scores from each model
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # This would typically fetch from a database of recent predictions
        return {
            "flow_id": flow_id,
            "explanation": "Detailed explanation would be retrieved from alerts database",
            "note": "Implement alerting database integration for full explainability history"
        }
    except Exception as e:
        logger.error(f"Explainability error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Get system metrics and statistics."""
    return {
        "message": "Metrics endpoint - integrate with Prometheus/Grafana",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/alerts", tags=["Alerts"])
async def get_recent_alerts(limit: int = 10):
    """Get recent alerts."""
    return {
        "message": f"Return last {limit} alerts from database",
        "note": "Implement alerts database integration",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": str(exc),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
