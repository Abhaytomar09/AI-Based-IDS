"""
Constants for IDS system
"""

# Feature names (adjust based on your dataset)
FEATURE_NAMES = [
    'duration', 'src_bytes', 'dst_bytes', 'bytes_per_packet',
    'packets_per_sec', 'src_dst_byte_ratio', 'protocol_TCP', 'protocol_UDP',
    'flag_SYN', 'flag_FIN', 'flag_RST', 'src_packets_sec', 'dst_packets_sec',
    'src_connections_last_60s', 'dst_connections_last_60s',
    'entropy_dst_ports', 'service_http', 'service_ftp', 'service_ssh',
    'mean_packet_size', 'std_packet_size', 'min_packet_size', 'max_packet_size'
]

# Attack types (adjust based on your dataset)
ATTACK_TYPES = {
    0: 'Normal',
    1: 'DoS',
    2: 'Probe',
    3: 'R2L',
    4: 'U2R',
    5: 'Backdoor'
}

ATTACK_TYPES_REVERSE = {v: k for k, v in ATTACK_TYPES.items()}

# Model parameters
MODEL_PATHS = {
    'xgb': 'models/xgb_model.joblib',
    'rf': 'models/rf_model.joblib',
    'ae': 'models/autoencoder.pth',
    'if': 'models/isolation_forest.joblib',
    'scaler': 'models/scaler.joblib',
    'feature_names': 'models/feature_names.json'
}

# Thresholds
DEFAULT_THRESHOLDS = {
    'anomaly_score': 2.5,
    'confidence': 0.6,
    'risk_score': 0.5,
    'fpr_threshold': 0.05  # False positive rate for anomaly detector
}

# Kafka settings
KAFKA_SETTINGS = {
    'broker': 'localhost:9092',
    'topic': 'network_flows',
    'group_id': 'ids_detector'
}

# Database
DB_PATH = 'alerts.db'
ALERTS_FILE = 'alerts.jsonl'

# Colors for visualization
ALERT_COLORS = {
    'Normal': '#2ecc71',
    'DoS': '#e74c3c',
    'Probe': '#f39c12',
    'R2L': '#9b59b6',
    'U2R': '#e91e63',
    'Backdoor': '#c0392b'
}
