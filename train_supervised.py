"""
Supervised learning models (XGBoost, RandomForest)
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    roc_curve, precision_recall_curve, auc, f1_score
)
from sklearn.utils.class_weight import compute_class_weight
import joblib
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, List
import shap

logger = logging.getLogger(__name__)


class SupervisedClassifier:
    """Train and evaluate supervised learning models."""
    
    def __init__(self, model_type: str = 'xgboost', random_state: int = 42):
        """
        Initialize classifier.
        
        Args:
            model_type: 'xgboost' or 'random_forest'
            random_state: Random seed
        """
        self.model_type = model_type
        self.random_state = random_state
        self.model = None
        self.feature_names = None
        self.class_labels = None
        self.class_weights = None
        self.explainer = None
        
        if model_type == 'xgboost':
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric='logloss',
                random_state=random_state,
                n_jobs=-1,
                verbosity=0
            )
        elif model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1,
                verbose=0
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def compute_class_weights(self, y: pd.Series) -> Dict[int, float]:
        """Compute class weights for imbalanced data."""
        classes = np.unique(y)
        weights = compute_class_weight('balanced', classes=classes, y=y)
        weight_dict = {i: w for i, w in zip(classes, weights)}
        logger.info(f"Class weights: {weight_dict}")
        self.class_weights = weight_dict
        return weight_dict
    
    def train(self, X: pd.DataFrame, y: pd.Series, 
              sample_weight: np.ndarray = None, validation_split: float = 0.1) -> Dict[str, Any]:
        """
        Train the classifier.
        
        Args:
            X: Feature dataframe
            y: Labels series
            sample_weight: Optional sample weights
            validation_split: Fraction for validation set
        
        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training {self.model_type} classifier...")
        
        self.feature_names = X.columns.tolist()
        self.class_labels = sorted(y.unique())
        
        # Compute class weights
        self.compute_class_weights(y)
        
        # Split for validation
        if validation_split > 0:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=validation_split, 
                random_state=self.random_state, stratify=y
            )
        else:
            X_train, X_val, y_train, y_val = X, None, y, None
        
        # Train
        if self.model_type == 'xgboost' and X_val is not None:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=10,
                verbose=False
            )
        else:
            if self.model_type == 'xgboost' and self.class_weights:
                scale_pos_weight = self.class_weights.get(1, 1)
                self.model.set_params(scale_pos_weight=scale_pos_weight)
            
            self.model.fit(X_train, y_train, sample_weight=sample_weight)
        
        logger.info("Training complete")
        
        # Evaluate
        metrics = {}
        if X_val is not None:
            y_pred_val = self.model.predict(X_val)
            y_proba_val = self.model.predict_proba(X_val)
            metrics['val_f1'] = f1_score(y_val, y_pred_val, average='weighted')
            logger.info(f"Validation F1-score: {metrics['val_f1']:.4f}")
        
        return metrics
    
    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Comprehensive evaluation.
        
        Args:
            X: Feature dataframe
            y: Labels series
        
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info("Evaluating model...")
        
        y_pred = self.model.predict(X)
        y_proba = self.model.predict_proba(X)
        
        # Metrics
        report = classification_report(y, y_pred, output_dict=True)
        cm = confusion_matrix(y, y_pred)
        
        metrics = {
            'classification_report': report,
            'confusion_matrix': cm,
            'overall_f1': f1_score(y, y_pred, average='weighted'),
            'overall_accuracy': (y_pred == y).sum() / len(y)
        }
        
        # ROC-AUC for binary classification
        if len(self.class_labels) == 2:
            roc_auc = roc_auc_score(y, y_proba[:, 1])
            metrics['roc_auc'] = roc_auc
            logger.info(f"ROC-AUC: {roc_auc:.4f}")
        
        logger.info(f"F1-score: {metrics['overall_f1']:.4f}")
        logger.info(f"Accuracy: {metrics['overall_accuracy']:.4f}")
        
        return metrics
    
    def get_feature_importance(self, top_k: int = 10) -> pd.DataFrame:
        """Get feature importance."""
        if self.model_type == 'xgboost':
            importance = self.model.get_booster().get_score(importance_type='weight')
        else:  # random_forest
            importance = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # Sort and get top k
        sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_k]
        df_imp = pd.DataFrame(sorted_imp, columns=['feature', 'importance'])
        
        return df_imp
    
    def predict_with_confidence(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Predict with confidence scores."""
        y_pred = self.model.predict(X)
        y_proba = self.model.predict_proba(X)
        confidence = y_proba.max(axis=1)
        
        return y_pred, confidence
    
    def explain_predictions(self, X: pd.DataFrame, sample_indices: List[int] = None) -> Dict[str, Any]:
        """Generate SHAP explanations (for XGBoost)."""
        if self.model_type != 'xgboost':
            logger.warning("SHAP explanation only supported for XGBoost")
            return {}
        
        if self.explainer is None:
            logger.info("Initializing SHAP explainer...")
            self.explainer = shap.TreeExplainer(self.model)
        
        if sample_indices is None:
            sample_indices = range(min(100, len(X)))  # Limit to 100 samples for speed
        
        X_sample = X.iloc[sample_indices]
        shap_values = self.explainer.shap_values(X_sample)
        
        # For multi-class, shap_values is a list
        explanations = {
            'shap_values': shap_values,
            'base_values': self.explainer.expected_value,
            'features': X_sample,
            'feature_names': self.feature_names
        }
        
        return explanations
    
    def save_model(self, path: str = "models/xgb_model.joblib"):
        """Save trained model."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        
        # Also save metadata
        metadata = {
            'feature_names': self.feature_names,
            'class_labels': self.class_labels,
            'class_weights': self.class_weights,
            'model_type': self.model_type
        }
        meta_path = path.replace('.joblib', '_meta.joblib')
        joblib.dump(metadata, meta_path)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str = "models/xgb_model.joblib"):
        """Load trained model."""
        self.model = joblib.load(path)
        
        # Load metadata
        meta_path = path.replace('.joblib', '_meta.joblib')
        if Path(meta_path).exists():
            metadata = joblib.load(meta_path)
            self.feature_names = metadata.get('feature_names')
            self.class_labels = metadata.get('class_labels')
            self.class_weights = metadata.get('class_weights')
        
        logger.info(f"Model loaded from {path}")


def train_and_save(data_path: str, output_dir: str = "models/", model_type: str = "xgboost"):
    """Train and save supervised model - main entry point."""
    logger.info(f"Training {model_type} classifier...")
    
    # Load data
    df = pd.read_csv(data_path)
    
    # Separate features and labels
    label_col = 'label'
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found in dataset")
    
    X = df.drop(columns=[label_col])
    y = df[label_col]
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Initialize and train
    classifier = SupervisedClassifier(model_type=model_type)
    classifier.train(X_train, y_train)
    
    # Evaluate
    metrics = classifier.evaluate(X_test, y_test)
    
    # Save
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model_file = f"{output_dir}{model_type}_model.joblib"
    classifier.save_model(model_file)
    
    logger.info(f"Model saved to {model_file}")
    return classifier, metrics


if __name__ == "__main__":
    # Example usage
    classifier, metrics = train_and_save("data/processed/train.csv")
    print(f"F1-score: {metrics['overall_f1']:.4f}")
