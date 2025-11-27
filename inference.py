"""
Inference engine - load and run models for predictions
"""
import numpy as np
import pandas as pd
import joblib
import torch
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List
from datetime import datetime

from src.train_supervised import SupervisedClassifier
from src.train_unsupervised import AnomalyDetector
from src.utils import create_alert, get_recommendation, get_feature_importance_text

logger = logging.getLogger(__name__)


class IDSInferenceEngine:
    """
    Unified inference engine combining supervised and unsupervised models.
    """
    
    def __init__(self, 
                 xgb_model_path: str = "models/xgb_model.joblib",
                 rf_model_path: str = "models/rf_model.joblib",
                 ae_model_path: str = "models/autoencoder.pth",
                 if_model_path: str = "models/isolation_forest.joblib",
                 scaler_path: str = "models/scaler.joblib",
                 feature_names_path: str = "models/feature_names.json"):
        """
        Initialize inference engine with pre-trained models.
        
        Args:
            xgb_model_path: Path to XGBoost model
            rf_model_path: Path to RandomForest model
            ae_model_path: Path to Autoencoder model
            if_model_path: Path to Isolation Forest model
            scaler_path: Path to feature scaler
            feature_names_path: Path to feature names JSON
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Load models
        self.xgb_classifier = SupervisedClassifier(model_type='xgboost')
        self.rf_classifier = SupervisedClassifier(model_type='random_forest')
        self.ae_detector = AnomalyDetector(model_type='autoencoder', device=str(self.device))
        self.if_detector = AnomalyDetector(model_type='isolation_forest')
        
        self.scaler = None
        self.feature_names = None
        
        try:
            if Path(xgb_model_path).exists():
                self.xgb_classifier.load_model(xgb_model_path)
                logger.info("XGBoost model loaded")
            
            if Path(rf_model_path).exists():
                self.rf_classifier.load_model(rf_model_path)
                logger.info("RandomForest model loaded")
            
            if Path(ae_model_path).exists():
                # Get n_features from feature names
                n_features = len(self.load_feature_names(feature_names_path)) if Path(feature_names_path).exists() else 22
                self.ae_detector.load_model(ae_model_path, n_features=n_features)
                logger.info("Autoencoder model loaded")
            
            if Path(if_model_path).exists():
                self.if_detector.load_model(if_model_path)
                logger.info("Isolation Forest model loaded")
            
            if Path(scaler_path).exists():
                self.scaler = joblib.load(scaler_path)
                logger.info("Scaler loaded")
            
            if Path(feature_names_path).exists():
                self.feature_names = self.load_feature_names(feature_names_path)
        
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    @staticmethod
    def load_feature_names(path: str) -> List[str]:
        """Load feature names."""
        if path.endswith('.json'):
            with open(path, 'r') as f:
                return json.load(f)
        else:
            return joblib.load(path)
    
    def preprocess_input(self, data: Dict[str, Any]) -> np.ndarray:
        """
        Convert input dictionary to feature array.
        
        Args:
            data: Dictionary with feature values
        
        Returns:
            Normalized feature array
        """
        # Create feature vector
        if self.feature_names:
            features = np.array([data.get(feat, 0.0) for feat in self.feature_names]).reshape(1, -1)
        else:
            features = np.array(list(data.values())).reshape(1, -1)
        
        # Scale if scaler available
        if self.scaler:
            features = self.scaler.transform(features)
        
        return features
    
    def predict_supervised(self, X: np.ndarray, model: str = 'xgboost') -> Tuple[
        np.ndarray, np.ndarray]:
        """
        Run supervised classifier.
        
        Args:
            X: Feature array
            model: 'xgboost' or 'random_forest'
        
        Returns:
            Tuple of (predictions, probabilities)
        """
        if model == 'xgboost':
            classifier = self.xgb_classifier
        else:
            classifier = self.rf_classifier
        
        if classifier.model is None:
            return None, None
        
        y_pred, confidence = classifier.predict_with_confidence(pd.DataFrame(X, columns=self.feature_names or range(X.shape[1])))
        y_proba = classifier.model.predict_proba(pd.DataFrame(X, columns=self.feature_names or range(X.shape[1])))
        
        return y_pred, y_proba
    
    def predict_anomaly(self, X: np.ndarray, model: str = 'autoencoder') -> Tuple[
        np.ndarray, np.ndarray]:
        """
        Run anomaly detector.
        
        Args:
            X: Feature array
            model: 'autoencoder' or 'isolation_forest'
        
        Returns:
            Tuple of (is_anomaly, scores)
        """
        if model == 'autoencoder':
            detector = self.ae_detector
        else:
            detector = self.if_detector
        
        if detector.model is None:
            return None, None
        
        is_anomaly, scores = detector.detect_anomalies(X, return_scores=True)
        return is_anomaly, scores
    
    def predict(self, data: Dict[str, Any], 
                supervised_weight: float = 0.6,
                anomaly_weight: float = 0.4,
                confidence_threshold: float = 0.6,
                anomaly_threshold: float = 2.5) -> Dict[str, Any]:
        """
        Make unified prediction combining supervised and unsupervised models.
        
        Args:
            data: Input flow data
            supervised_weight: Weight for supervised model (0-1)
            anomaly_weight: Weight for anomaly score (0-1)
            confidence_threshold: Threshold for classification confidence
            anomaly_threshold: Threshold for anomaly detection
        
        Returns:
            Dictionary with prediction results and alert info
        """
        # Preprocess
        X = self.preprocess_input(data)
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'flow_id': f"{data.get('src_ip', 'unknown')}:{data.get('src_port', '?')}->" \
                      f"{data.get('dst_ip', 'unknown')}:{data.get('dst_port', '?')}",
            'models': {},
            'alert': None
        }
        
        # Supervised prediction
        sup_pred, sup_proba = self.predict_supervised(X, model='xgboost')
        if sup_pred is not None:
            sup_confidence = sup_proba.max()
            pred_class = sup_pred[0]
            
            result['models']['supervised'] = {
                'prediction': int(pred_class),
                'confidence': float(sup_confidence),
                'probabilities': sup_proba[0].tolist()
            }
        
        # Anomaly prediction
        is_anomaly, anomaly_scores = self.predict_anomaly(X, model='autoencoder')
        if is_anomaly is not None:
            result['models']['anomaly'] = {
                'is_anomaly': bool(is_anomaly[0]),
                'score': float(anomaly_scores[0])
            }
        
        # Ensemble decision
        alert_type = None
        alert_confidence = 0.0
        
        if sup_pred is not None and sup_confidence > confidence_threshold:
            alert_type = str(sup_pred[0])
            alert_confidence = sup_confidence
        elif is_anomaly is not None and is_anomaly[0]:
            alert_type = 'Anomaly'
            alert_confidence = min(1.0, anomaly_scores[0] / anomaly_threshold)
        
        # Create alert if detected
        if alert_type:
            top_features = self.get_top_features(X)
            
            alert = create_alert(
                timestamp=result['timestamp'],
                flow_id=result['flow_id'],
                alert_type=alert_type,
                confidence=alert_confidence,
                top_features=top_features,
                anomaly_score=float(anomaly_scores[0]) if is_anomaly is not None else 0.0,
                flow_context=data,
                recommended_action=get_recommendation(alert_type, alert_confidence)
            )
            result['alert'] = alert
        
        return result
    
    def get_top_features(self, X: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """Get top contributing features."""
        top_features = []
        
        try:
            if self.xgb_classifier.model is not None:
                importance_df = self.xgb_classifier.get_feature_importance(top_k=top_k)
                
                # Normalize
                total = importance_df['importance'].sum()
                if total > 0:
                    for _, row in importance_df.iterrows():
                        top_features.append({
                            'feature': row['feature'],
                            'impact': float(row['importance'] / total)
                        })
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
        
        return top_features
    
    def batch_predict(self, data_path: str, output_path: str = "predictions.jsonl") -> Dict[str, Any]:
        """
        Run inference on batch of data.
        
        Args:
            data_path: Path to CSV with test data
            output_path: Path to save predictions
        
        Returns:
            Summary statistics
        """
        logger.info(f"Running batch inference on {data_path}")
        
        df = pd.read_csv(data_path)
        
        results = []
        alert_count = 0
        
        for idx, row in df.iterrows():
            data = row.to_dict()
            prediction = self.predict(data)
            
            if prediction['alert']:
                alert_count += 1
            
            results.append(prediction)
        
        # Save predictions
        with open(output_path, 'w') as f:
            for result in results:
                json.dump(result, f)
                f.write('\n')
        
        logger.info(f"Processed {len(results)} samples, {alert_count} alerts")
        
        return {
            'total_samples': len(results),
            'alerts_triggered': alert_count,
            'alert_rate': alert_count / len(results) if results else 0.0
        }


# Singleton instance
_inference_engine = None


def get_inference_engine(force_reload: bool = False) -> IDSInferenceEngine:
    """Get or create singleton inference engine."""
    global _inference_engine
    
    if _inference_engine is None or force_reload:
        _inference_engine = IDSInferenceEngine()
    
    return _inference_engine


if __name__ == "__main__":
    engine = get_inference_engine()
    
    # Test prediction
    test_data = {
        'src_ip': '192.168.1.100',
        'dst_ip': '10.0.0.5',
        'src_port': 12345,
        'dst_port': 80,
        'duration': 10.5,
        'src_bytes': 1024,
        'dst_bytes': 512,
        'num_packets': 50,
    }
    
    result = engine.predict(test_data)
    print(json.dumps(result, indent=2))
