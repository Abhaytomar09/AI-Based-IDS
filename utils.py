"""
Utility functions for IDS system
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "ids.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        'supervised': {
            'model_type': 'xgboost',
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.1
        },
        'unsupervised': {
            'autoencoder': {
                'hidden_dim': 64,
                'bottleneck_dim': 16,
                'epochs': 50,
                'learning_rate': 0.001
            },
            'isolation_forest': {
                'n_estimators': 100,
                'contamination': 0.05
            }
        },
        'thresholds': {
            'anomaly_score_threshold': 2.5,
            'supervised_confidence': 0.6,
            'ensemble_risk_score': 0.5
        },
        'streaming': {
            'kafka_broker': 'localhost:9092',
            'topic': 'network_flows',
            'consumer_group': 'ids_detector',
            'batch_size': 32
        },
        'api': {
            'host': '0.0.0.0',
            'port': 8000,
            'reload': True
        }
    }


def create_alert(
    timestamp: str,
    flow_id: str,
    alert_type: str,
    confidence: float,
    top_features: List[Dict[str, Any]],
    anomaly_score: float,
    flow_context: Dict[str, Any],
    recommended_action: str = "Review"
) -> Dict[str, Any]:
    """Create structured alert dictionary."""
    return {
        'timestamp': timestamp,
        'flow_id': flow_id,
        'alert_type': alert_type,
        'confidence': round(confidence, 4),
        'top_features': top_features,
        'anomaly_score': round(anomaly_score, 4),
        'flow_context': flow_context,
        'recommended_action': recommended_action
    }


def save_alert(alert: Dict[str, Any], output_file: str = "alerts.jsonl"):
    """Append alert to JSONL file for continuous learning."""
    with open(output_file, 'a') as f:
        f.write(json.dumps(alert) + '\n')
    logger.info(f"Alert saved: {alert['flow_id']} - {alert['alert_type']}")


def load_alerts(input_file: str = "alerts.jsonl") -> List[Dict[str, Any]]:
    """Load all alerts from JSONL file."""
    alerts = []
    if Path(input_file).exists():
        with open(input_file, 'r') as f:
            for line in f:
                alerts.append(json.loads(line))
    return alerts


def normalize_features(features: Dict[str, float], feature_min: Dict, feature_max: Dict) -> Dict[str, float]:
    """Min-Max normalize features."""
    normalized = {}
    for key, val in features.items():
        if key in feature_min and key in feature_max:
            denom = feature_max[key] - feature_min[key]
            if denom > 0:
                normalized[key] = (val - feature_min[key]) / denom
            else:
                normalized[key] = val
        else:
            normalized[key] = val
    return normalized


def get_feature_importance_text(features: List[Dict[str, Any]], top_k: int = 5) -> str:
    """Generate human-readable feature importance explanation."""
    top_features = sorted(features, key=lambda x: x['impact'], reverse=True)[:top_k]
    explanation = "Top contributing factors: "
    explanations = []
    for i, feat in enumerate(top_features, 1):
        impact_pct = round(feat['impact'] * 100, 1)
        explanations.append(f"{feat['feature']} ({impact_pct}%)")
    explanation += ", ".join(explanations)
    return explanation


def get_recommendation(alert_type: str, confidence: float) -> str:
    """Get recommended action based on alert type and confidence."""
    if confidence > 0.9:
        if alert_type in ['DDoS', 'Probe']:
            return "Block source IP and investigate"
        elif alert_type == 'Backdoor':
            return "Isolate host immediately"
        else:
            return "Escalate to security team"
    elif confidence > 0.7:
        return "Review and monitor"
    else:
        return "Monitor and log"


if __name__ == "__main__":
    config = load_config()
    logger.info(f"Loaded config: {config}")
