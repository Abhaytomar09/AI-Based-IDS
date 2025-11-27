# AI-Powered Intrusion Detection System (IDS) - Final Year Project

## Overview

This project implements a hybrid **Machine Learning + Deep Learning** approach to network intrusion detection. It combines:

- **Supervised Learning**: XGBoost/RandomForest for known attack classification
- **Unsupervised Learning**: Autoencoders + Isolation Forest for anomaly/zero-day detection
- **Real-time Processing**: Kafka-based streaming pipeline with FastAPI inference
- **Explainability**: SHAP integration for interpretable alerts
- **Continuous Learning**: Framework for periodic retraining with feedback

## Key Features

✅ Hybrid ML/DL models (supervised + unsupervised ensemble)  
✅ Real-time network flow detection  
✅ SHAP-based explainability for all predictions  
✅ Streamlit dashboard for monitoring and alerts  
✅ FastAPI inference service  
✅ Docker containerization for easy deployment  
✅ Kafka producer/consumer for streaming simulation  
✅ Comprehensive evaluation metrics (ROC, PR, confusion matrix)  
✅ Adversarial robustness testing  
✅ Complete Jupyter notebooks for reproducibility  

## Project Structure

```
ai-ids/
├── src/                          # Source code
│   ├── preprocessing.py         # Data loading & feature engineering
│   ├── train_supervised.py      # XGBoost/RandomForest training
│   ├── train_unsupervised.py    # Autoencoder & Isolation Forest
│   ├── inference.py             # Model loading & prediction logic
│   ├── api.py                   # FastAPI service
│   ├── kafka_producer.py        # Kafka stream producer (replay)
│   ├── kafka_consumer.py        # Kafka stream consumer (detection)
│   ├── dashboard.py             # Streamlit UI
│   └── utils.py                 # Helper functions
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_supervised_training.ipynb
│   ├── 03_unsupervised_training.ipynb
│   ├── 04_evaluation_and_metrics.ipynb
│   ├── 05_explainability_demo.ipynb
│   └── 06_adversarial_robustness.ipynb
├── data/
│   ├── raw/                     # Original datasets (NSL-KDD, CIC-IDS2017, etc.)
│   ├── processed/               # Preprocessed & split datasets
│   └── sample_flows.csv         # Small test dataset
├── models/
│   ├── xgb_model.joblib         # Trained XGBoost classifier
│   ├── rf_model.joblib          # Trained RandomForest classifier
│   ├── autoencoder.pth          # Trained PyTorch autoencoder
│   ├── isolation_forest.joblib  # Trained Isolation Forest
│   ├── scaler.joblib            # StandardScaler (for feature normalization)
│   └── feature_names.json       # Feature engineering metadata
├── config/
│   ├── settings.yaml            # Model & pipeline configurations
│   └── constants.py             # Global constants
├── docker/
│   ├── Dockerfile.api           # FastAPI container
│   ├── Dockerfile.consumer      # Kafka consumer container
│   └── Dockerfile.dashboard     # Streamlit dashboard container
├── docker-compose.yml           # Orchestration for all services
├── requirements.txt             # Python dependencies
├── environment.yml              # Conda environment file
├── .env.example                 # Example environment variables
└── README.md                    # This file
```

## Installation & Setup

### 1. Clone & Navigate
```bash
cd ai-ids
```

### 2. Create Virtual Environment

**Using conda** (recommended for PyTorch):
```bash
conda env create -f environment.yml
conda activate ai-ids
```

**Using venv**:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Download Dataset

Download one of the recommended datasets and place in `data/raw/`:
- **NSL-KDD**: [NSL-KDD Benchmark](https://www.unb.ca/cic/datasets/nsl.html)
- **CIC-IDS2017**: [CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html)
- **UNSW-NB15**: [UNSW-NB15](https://www.unsw.adfa.edu.au/unsw-canberra/academic/school-of-cyber-security/cybersecurity/datasets)

Expected format: CSV with columns like `duration`, `src_bytes`, `dst_bytes`, `label`, etc.

### 4. Preprocess Data

```bash
python -c "from src.preprocessing import load_and_preprocess; load_and_preprocess('data/raw/your_dataset.csv', 'data/processed/')"
```

### 5. Train Models

**Supervised model**:
```bash
python -c "from src.train_supervised import train_and_save; train_and_save('data/processed/train.csv')"
```

**Unsupervised model**:
```bash
python -c "from src.train_unsupervised import train_and_save; train_and_save('data/processed/train_normal.csv')"
```

## Quick Start (with sample data)

A minimal `data/sample_flows.csv` is included for quick testing:

```bash
# Train on sample
python src/train_supervised.py --data data/sample_flows.csv --output models/

# Launch API
python src/api.py

# Open dashboard in another terminal
streamlit run src/dashboard.py
```

## Usage

### Option 1: Batch Inference (Jupyter notebooks)

See `notebooks/02_supervised_training.ipynb` and `notebooks/03_unsupervised_training.ipynb` for full walkthrough.

### Option 2: Real-time API

**Start the FastAPI server**:
```bash
python src/api.py
```

**Send a prediction request**:
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"duration": 10.5, "src_bytes": 1024, "dst_bytes": 512, ...}'
```

### Option 3: Streaming with Kafka

**Terminal 1 - Start Kafka & Zookeeper** (via Docker):
```bash
docker-compose -f docker-compose.yml up kafka zookeeper
```

**Terminal 2 - Kafka Producer** (replay dataset):
```bash
python src/kafka_producer.py --data data/processed/test.csv --speed 10
```

**Terminal 3 - Kafka Consumer** (detection pipeline):
```bash
python src/kafka_consumer.py
```

**Terminal 4 - Dashboard**:
```bash
streamlit run src/dashboard.py
```

## Model Architecture

### Supervised Classifier (Known Attacks)

```
Input Features (30-50 dims)
    ↓
Feature Scaling (StandardScaler)
    ↓
XGBoost / RandomForest
    ↓
Output: Probabilities for [Normal, DoS, Probe, R2L, U2R, ...]
    ↓
SHAP Feature Importance
```

### Unsupervised Anomaly Detector (Zero-day)

```
Normal Training Data (30-50 dims)
    ↓
Autoencoder (Encoder → Bottleneck → Decoder)
    ↓
Learns Compressed Normal Representation
    ↓
Test Flow
    ↓
Reconstruction Error (MSE)
    ↓
If error > threshold → ANOMALY DETECTED
    ↓
Also run Isolation Forest (complementary check)
```

### Ensemble Decision Logic

```
For each incoming flow:
  1. Supervised model → P(attack), predicted_class
  2. Anomaly detector → reconstruction_error, is_anomaly
  3. Combine scores:
     risk_score = α * P(attack) + β * normalized_error
  4. If risk_score > detection_threshold:
     - Alert with timestamp, flow details, top SHAP features, anomaly score
     - Log for continuous learning feedback
```

## Evaluation Metrics

### Supervised Model
- **Precision, Recall, F1-Score** per attack type
- **Confusion Matrix** for multi-class classification
- **ROC-AUC & PR-AUC** for attack vs normal
- **Per-class metrics** (DoS, Probe, R2L, U2R, normal)

### Unsupervised Model
- **ROC-AUC** (if labels available for evaluation)
- **Precision@k** at various False Positive Rates
- **True Positive Rate at 1% FPR** (operationally important)

### Operational Metrics
- **Latency**: Time per prediction (ms)
- **Throughput**: Flows processed per second
- **Memory**: Model size & inference RAM usage
- **False Positive Rate**: Key metric for SOC efficiency

## Explainability

All alerts include:

1. **SHAP Summary**: Top 5 features that contributed to the decision
2. **Flow Context**: Source IP, destination IP, ports, protocol, bytes, packets
3. **Model Confidence**: Probability scores from both classifiers
4. **Anomaly Score**: Reconstruction error and Isolation Forest scores
5. **Decision Justification**: Human-readable explanation (e.g., "High byte rate + many SYN flags in 10s window")

Example alert:
```json
{
  "timestamp": "2024-01-15T10:23:45",
  "flow_id": "192.168.1.100:12345->10.0.0.5:80",
  "alert_type": "DDoS",
  "confidence": 0.94,
  "top_features": [
    {"feature": "src_packets_sec", "impact": 0.32},
    {"feature": "dst_bytes", "impact": 0.28},
    {"feature": "src_dst_byte_ratio", "impact": 0.21},
    {"feature": "protocol_TCP", "impact": 0.15},
    {"feature": "flag_SYN", "impact": 0.12}
  ],
  "anomaly_score": 0.05,
  "recommended_action": "Block source IP"
}
```

## Continuous Learning

The system is designed for feedback-driven retraining:

1. **Alert Storage**: All detections logged to JSON/database
2. **Human Review**: SOC analyst confirms true/false positives
3. **Label Collection**: Confirmed labels appended to training dataset
4. **Periodic Retraining**: Weekly job retrains models with new data
5. **Model Versioning**: Old models preserved; A/B testing of new versions

See `notebooks/06_continuous_learning.ipynb` for implementation.

## Adversarial Robustness

Tested against:
- **Feature scaling attacks**: Magnitude scaling of bytes/packets
- **Timing attacks**: Modified duration/packet inter-arrival times
- **Masking attacks**: Mimicking normal patterns

See `notebooks/05_adversarial_robustness.ipynb` for full analysis.

## Docker Deployment

### Build & Run All Services

```bash
docker-compose up --build
```

This starts:
- **Kafka** (port 9092): Message broker
- **Zookeeper** (port 2181): Kafka coordination
- **FastAPI** (port 8000): Inference endpoint
- **Streamlit Dashboard** (port 8501): Web UI
- **Consumer** (background): Processes Kafka streams

### Access Services

- Dashboard: http://localhost:8501
- API Docs: http://localhost:8000/docs
- API Redoc: http://localhost:8000/redoc

### Build Individual Containers

```bash
# API only
docker build -f docker/Dockerfile.api -t ai-ids-api:latest .
docker run -p 8000:8000 ai-ids-api:latest

# Consumer only
docker build -f docker/Dockerfile.consumer -t ai-ids-consumer:latest .
docker run ai-ids-consumer:latest

# Dashboard only
docker build -f docker/Dockerfile.dashboard -t ai-ids-dashboard:latest .
docker run -p 8501:8501 ai-ids-dashboard:latest
```

## Notebooks

### 1. Data Exploration (`01_data_exploration.ipynb`)
- Load and explore datasets
- Statistical analysis & visualizations
- Class distribution, feature correlations
- Handling missing values & outliers

### 2. Supervised Training (`02_supervised_training.ipynb`)
- Feature engineering & preprocessing
- Train XGBoost & RandomForest
- Cross-validation & hyperparameter tuning
- Evaluate with confusion matrix, ROC-AUC, F1-scores
- SHAP explainability analysis

### 3. Unsupervised Training (`03_unsupervised_training.ipynb`)
- Train Autoencoder on normal-only data
- Train Isolation Forest
- Calibrate anomaly detection thresholds
- Visualize reconstructions & anomaly scores

### 4. Evaluation & Metrics (`04_evaluation_and_metrics.ipynb`)
- Comprehensive evaluation on test set
- Per-attack-type performance
- ROC/PR curves & AUC comparisons
- Operational metrics (latency, throughput)
- Baseline comparisons

### 5. Explainability Demo (`05_explainability_demo.ipynb`)
- SHAP force plots & summary plots
- Feature importance across attack types
- Individual prediction explanations
- Trust & interpretability analysis

### 6. Adversarial Robustness (`06_adversarial_robustness.ipynb`)
- Perturbation tests
- Detection rate under attacks
- Mitigation strategies
- Robustness evaluation

## Configuration

### `config/settings.yaml`

```yaml
# Model parameters
supervised:
  model_type: "xgboost"  # or "random_forest"
  n_estimators: 200
  max_depth: 6
  learning_rate: 0.1

unsupervised:
  autoencoder:
    hidden_dim: 64
    bottleneck_dim: 16
    epochs: 50
    learning_rate: 0.001
  isolation_forest:
    n_estimators: 100
    contamination: 0.05

# Thresholds
thresholds:
  anomaly_score_threshold: 2.5  # reconstruction error threshold
  supervised_confidence: 0.6     # classification confidence threshold
  ensemble_risk_score: 0.5       # combined risk score

# Operational
streaming:
  kafka_broker: "localhost:9092"
  topic: "network_flows"
  consumer_group: "ids_detector"
  batch_size: 32

api:
  host: "0.0.0.0"
  port: 8000
  reload: true
```

## Performance Targets (Based on Academic Benchmarks)

- **Supervised Model**: F1 > 0.90 on known attacks
- **Anomaly Detection**: TPR > 0.85 @ FPR < 0.05
- **Latency**: < 10ms per flow (on GPU) / < 50ms per flow (CPU)
- **Throughput**: > 10,000 flows/sec
- **False Positive Rate**: < 2% (operational constraint)

## Ethical Considerations

✅ **Privacy**: No payload inspection; only flow-level statistics  
✅ **Consent**: Used only on authorized networks (with proper ethics approval)  
✅ **Bias**: Dataset sampling strategy documented; model fairness analyzed  
✅ **Transparency**: All detections logged and explainable  
✅ **Audit Trail**: Complete history of alerts, retraining, and feedback  

## References & Further Reading

1. **Classic IDS Papers**:
   - Denning, D. E. (1987). "An Intrusion Detection Model"
   - Liao et al. (2013). "Intrusion Detection System: A Comprehensive Review"

2. **ML for Cybersecurity**:
   - Goodfellow et al. (2016). "Deep Learning" (Chapter on adversarial examples)
   - Sharafaldin et al. (2018). "CIC-IDS2017" dataset paper

3. **Explainability**:
   - Lundberg & Lee (2017). "A Unified Approach to Interpreting Model Predictions" (SHAP)
   - Ribeiro et al. (2016). "Why Should I Trust You?" (LIME)

4. **Anomaly Detection**:
   - Liu et al. (2012). "Isolation Forest"
   - Goldstein & Uchida (2016). "A Comparative Evaluation of Unsupervised Anomaly Detection Algorithms"

## License

This project is provided for educational purposes. Adapt and extend as needed for your final-year submission.

## Support & Troubleshooting

### GPU Not Detected
```bash
# Check PyTorch/CUDA setup
python -c "import torch; print(torch.cuda.is_available())"
```

### Kafka Connection Issues
```bash
# Check if Kafka is running
docker ps | grep kafka
# Restart
docker-compose restart kafka
```

### Out of Memory
- Reduce `batch_size` in config
- Use CPU-only mode (remove GPU calls in `train_unsupervised.py`)
- Sample larger datasets (e.g., use 50% of data)

### Models Not Found
```bash
# Ensure models directory exists and contains trained artifacts
ls -la models/
# If empty, re-run training scripts
python src/train_supervised.py
python src/train_unsupervised.py
```

## Submission Checklist

- [ ] All source code in `src/`
- [ ] README.md with complete documentation
- [ ] requirements.txt & environment.yml
- [ ] Trained models in `models/`
- [ ] Sample dataset in `data/sample_flows.csv`
- [ ] All 6 Jupyter notebooks with outputs
- [ ] Docker & docker-compose files
- [ ] Final report (PDF) with results & analysis
- [ ] Presentation slides
- [ ] Demo video (5-10 min, showing dashboard)
- [ ] `.env.example` with configuration template

---

**Ready to build your capstone project!** 🚀
