# Quick Reference Guide

## File Structure Reference

```
ai-ids/
├── src/
│   ├── preprocessing.py      → Data loading, cleaning, feature engineering
│   ├── train_supervised.py   → XGBoost, RandomForest training & evaluation
│   ├── train_unsupervised.py → Autoencoder, Isolation Forest training
│   ├── inference.py          → Unified prediction engine
│   ├── api.py                → FastAPI web service
│   ├── kafka_producer.py     → Stream producer (dataset replay)
│   ├── kafka_consumer.py     → Stream consumer (real-time detection)
│   ├── dashboard.py          → Streamlit web UI
│   ├── utils.py              → Helper functions
│   └── constants.py          → Global constants & configs
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_supervised_training.ipynb
│   ├── 03_unsupervised_training.ipynb
│   ├── 04_evaluation_and_metrics.ipynb
│   ├── 05_explainability_demo.ipynb
│   └── 06_adversarial_robustness.ipynb
├── config/
│   └── settings.yaml         → All tunable parameters
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.consumer
│   └── Dockerfile.dashboard
├── data/
│   ├── sample_flows.csv      → Sample data for testing
│   ├── raw/                  → Download datasets here
│   └── processed/            → Generated preprocessed data
└── models/                   → Trained model artifacts
```

## Common Commands

### 1. Data Preparation
```bash
# Preprocess dataset
python -c "from src.preprocessing import load_and_preprocess; load_and_preprocess('data/raw/your_dataset.csv', 'data/processed/')"
```

### 2. Model Training
```bash
# Train supervised model
python -c "from src.train_supervised import train_and_save; train_and_save('data/processed/train.csv', 'models/', 'xgboost')"

# Train unsupervised models
python -c "from src.train_unsupervised import train_and_save_anomaly_detectors; train_and_save_anomaly_detectors('data/processed/train_normal.csv', 'models/')"
```

### 3. Run Services
```bash
# API Server (Port 8000)
python src/api.py

# Dashboard (Port 8501)
streamlit run src/dashboard.py

# Kafka Consumer
python -m src.kafka_consumer --broker localhost:9092

# Kafka Producer (replay dataset)
python -m src.kafka_producer --data data/processed/test.csv --speed 10
```

### 4. Docker Operations
```bash
# Start all services
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose build api
```

### 5. Model Testing
```bash
# Quick inference test
python -c "
from src.inference import get_inference_engine
engine = get_inference_engine()
result = engine.predict({
    'src_ip': '192.168.1.100',
    'dst_ip': '10.0.0.5',
    'src_port': 12345,
    'dst_port': 80,
    'duration': 10.5,
    'src_bytes': 1024,
    'dst_bytes': 512,
    'num_packets': 50
})
print(result)
"
```

## Configuration Tips

### Adjust Detection Thresholds (config/settings.yaml)
```yaml
thresholds:
  supervised_confidence: 0.6      # Lower = more alerts
  anomaly_score_threshold: 2.5    # Lower = more alerts
  ensemble_risk_score: 0.5        # Combined threshold
```

### Tune Model Parameters
```yaml
supervised:
  n_estimators: 200    # More = better accuracy (slower)
  max_depth: 6         # Lower = simpler model (less overfit)
  learning_rate: 0.1   # Learning speed

unsupervised:
  autoencoder:
    hidden_dims: [64, 32]  # Layer sizes
    epochs: 50             # Training epochs
```

## API Usage Examples

### Single Prediction
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.5",
    "src_port": 12345,
    "dst_port": 80,
    "protocol": "TCP",
    "duration": 10.5,
    "src_bytes": 1024,
    "dst_bytes": 512,
    "num_packets": 50
  }'
```

### Batch Prediction
```bash
curl -X POST http://localhost:8000/batch \
  -H "Content-Type: application/json" \
  -d '{
    "flows": [
      {"src_ip": "192.168.1.100", ...},
      {"src_ip": "192.168.1.101", ...}
    ]
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

### API Documentation
```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

## Monitoring & Logging

### View Logs
```bash
# API logs
tail -f logs/ids.log

# Docker logs
docker-compose logs -f api

# Dashboard output
streamlit run src/dashboard.py --logger.level=debug
```

### Alert Files
```bash
# View recent alerts
tail -f alerts.jsonl

# Parse alerts (Python)
import json
with open('alerts.jsonl', 'r') as f:
    for line in f:
        alert = json.loads(line)
        print(f"{alert['timestamp']} - {alert['alert_type']} - {alert['flow_id']}")
```

## Performance Optimization

### For Production
1. **Use GPU**: Set CUDA_VISIBLE_DEVICES
2. **Batch Processing**: Increase batch_size in config
3. **Model Quantization**: Convert models to TensorRT
4. **Caching**: Enable Redis caching in API
5. **Load Balancing**: Multiple API instances with Nginx

### For Development
1. **Smaller Datasets**: Use sample data for quick testing
2. **Reduced Epochs**: Set epochs=10 for autoencoder
3. **Smaller Batches**: batch_size=16 for low RAM
4. **Verbose Logging**: Set LOG_LEVEL=DEBUG

## Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -r requirements.txt` |
| CUDA not found | Set `DEVICE = torch.device('cpu')` |
| Port already in use | `lsof -i :8000` and `kill -9 <PID>` |
| Kafka connection failed | `docker-compose restart kafka` |
| Out of memory | Reduce batch_size in config |
| Models not found | Run training scripts first |
| Dashboard not loading | Check `streamlit run src/dashboard.py` output |

## Feature Engineering Explanation

```python
# Key engineered features in preprocessing.py:

bytes_per_packet      = src_bytes / num_packets     # Average packet size
packets_per_sec       = num_packets / duration      # Flow rate
src_dst_byte_ratio    = src_bytes / dst_bytes       # Asymmetry
bytes_per_sec         = src_bytes / duration        # Bandwidth
total_bytes           = src_bytes + dst_bytes       # Total traffic
num_flags             = SYN + FIN + RST + ...       # Control flags
entropy_dst_ports     = Shannon entropy of dest IPs # Destination diversity
```

## Model Output Interpretation

### Supervised Classifier Output
```json
{
  "prediction": 1,           // 0=Normal, 1=DoS, 2=Probe, 3=R2L, 4=U2R, 5=Backdoor
  "confidence": 0.94,        // Probability of predicted class
  "probabilities": [0.02, 0.94, 0.02, 0.01, 0.01, 0.00]  // All classes
}
```

### Anomaly Detector Output
```json
{
  "is_anomaly": false,       // True if anomaly detected
  "score": 1.8               // Reconstruction error (higher = more anomalous)
}
```

### Alert Structure
```json
{
  "timestamp": "2024-01-15T10:23:45",
  "flow_id": "192.168.1.100:12345->10.0.0.5:80",
  "alert_type": "DDoS",
  "confidence": 0.94,
  "top_features": [
    {"feature": "src_packets_sec", "impact": 0.32},
    {"feature": "dst_bytes", "impact": 0.28}
  ],
  "anomaly_score": 0.05,
  "recommended_action": "Block source IP"
}
```

## Next Steps After Setup

1. **Week 1-2**: Download dataset, run preprocessing
2. **Week 3-4**: Train supervised & unsupervised models
3. **Week 5**: Evaluate models, generate SHAP explanations
4. **Week 6**: Build API and test inference
5. **Week 7**: Deploy with Docker, streaming demo
6. **Week 8**: Write report, prepare presentation

---

**Happy coding! Questions? Check README.md for full documentation.**
