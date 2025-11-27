"""
Unsupervised anomaly detection models (Autoencoder, Isolation Forest)
"""
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, List
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Device setup
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger.info(f"Using device: {DEVICE}")


class Autoencoder(nn.Module):
    """Deep autoencoder for anomaly detection."""
    
    def __init__(self, n_features: int, hidden_dims: List[int] = None, 
                 bottleneck_dim: int = 16, activation: str = 'relu'):
        """
        Initialize autoencoder.
        
        Args:
            n_features: Number of input features
            hidden_dims: List of hidden layer dimensions
            bottleneck_dim: Dimension of bottleneck layer
            activation: Activation function ('relu' or 'tanh')
        """
        super().__init__()
        
        if hidden_dims is None:
            hidden_dims = [64, 32]
        
        self.n_features = n_features
        self.activation = getattr(torch, activation) if isinstance(activation, str) else activation
        
        # Encoder
        encoder_layers = []
        prev_dim = n_features
        for hidden_dim in hidden_dims:
            encoder_layers.append(nn.Linear(prev_dim, hidden_dim))
            encoder_layers.append(nn.ReLU())
            prev_dim = hidden_dim
        
        encoder_layers.append(nn.Linear(prev_dim, bottleneck_dim))
        encoder_layers.append(nn.ReLU())
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Decoder
        decoder_layers = []
        dims = [bottleneck_dim] + list(reversed(hidden_dims))
        for i in range(len(dims) - 1):
            decoder_layers.append(nn.Linear(dims[i], dims[i + 1]))
            decoder_layers.append(nn.ReLU())
        
        decoder_layers.append(nn.Linear(dims[-1], n_features))
        
        self.decoder = nn.Sequential(*decoder_layers)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass."""
        z = self.encoder(x)
        x_recon = self.decoder(z)
        return x_recon, z
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Get latent representation."""
        return self.encoder(x)


class AnomalyDetector:
    """Train and manage anomaly detection models."""
    
    def __init__(self, model_type: str = 'autoencoder', device: str = None):
        """
        Initialize anomaly detector.
        
        Args:
            model_type: 'autoencoder' or 'isolation_forest'
            device: 'cuda' or 'cpu'
        """
        self.model_type = model_type
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.scaler = StandardScaler()
        self.reconstruction_errors_train = None
        self.threshold = None
        self.feature_names = None
    
    def train_autoencoder(self, X: np.ndarray, epochs: int = 50, 
                         batch_size: int = 128, learning_rate: float = 0.001,
                         hidden_dims: List[int] = None, bottleneck_dim: int = 16,
                         validation_split: float = 0.1, patience: int = 5) -> Dict[str, Any]:
        """
        Train autoencoder.
        
        Args:
            X: Training data (normal samples only)
            epochs: Number of epochs
            batch_size: Batch size
            learning_rate: Learning rate
            hidden_dims: Hidden layer dimensions
            bottleneck_dim: Bottleneck dimension
            validation_split: Validation set fraction
            patience: Early stopping patience
        
        Returns:
            Dictionary with training history
        """
        logger.info("Training autoencoder...")
        
        if hidden_dims is None:
            hidden_dims = [64, 32]
        
        # Normalize
        X_scaled = self.scaler.fit_transform(X)
        
        # Create datasets
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        
        if validation_split > 0:
            n_val = int(len(X_tensor) * validation_split)
            indices = torch.randperm(len(X_tensor))
            val_indices = indices[:n_val]
            train_indices = indices[n_val:]
            
            X_train = X_tensor[train_indices]
            X_val = X_tensor[val_indices]
            
            train_dataset = TensorDataset(X_train)
            val_dataset = TensorDataset(X_val)
        else:
            train_dataset = TensorDataset(X_tensor)
            val_dataset = None
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        if val_dataset:
            val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Initialize model
        self.model = Autoencoder(
            n_features=X.shape[1],
            hidden_dims=hidden_dims,
            bottleneck_dim=bottleneck_dim
        ).to(self.device)
        
        optimizer = Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training loop
        history = {'train_loss': [], 'val_loss': []}
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            # Train
            self.model.train()
            train_loss = 0
            for batch, in train_loader:
                batch = batch.to(self.device)
                recon, _ = self.model(batch)
                loss = criterion(recon, batch)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item() * batch.size(0)
            
            train_loss /= len(train_dataset)
            history['train_loss'].append(train_loss)
            
            # Validation
            if val_dataset:
                self.model.eval()
                val_loss = 0
                with torch.no_grad():
                    for batch, in val_loader:
                        batch = batch.to(self.device)
                        recon, _ = self.model(batch)
                        loss = criterion(recon, batch)
                        val_loss += loss.item() * batch.size(0)
                
                val_loss /= len(val_dataset)
                history['val_loss'].append(val_loss)
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if (epoch + 1) % 10 == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs} - Train: {train_loss:.4f}, Val: {val_loss:.4f}")
                
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch + 1}")
                    break
            else:
                if (epoch + 1) % 10 == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs} - Train: {train_loss:.4f}")
        
        logger.info("Autoencoder training complete")
        
        # Compute reconstruction errors on training data
        self.model.eval()
        with torch.no_grad():
            X_recon, _ = self.model(X_tensor.to(self.device))
            self.reconstruction_errors_train = torch.mean(
                (X_tensor.to(self.device) - X_recon) ** 2, dim=1
            ).cpu().numpy()
        
        return history
    
    def train_isolation_forest(self, X: np.ndarray, contamination: float = 0.05,
                              n_estimators: int = 100) -> Dict[str, Any]:
        """
        Train Isolation Forest.
        
        Args:
            X: Training data (normal samples)
            contamination: Expected proportion of outliers
            n_estimators: Number of trees
        
        Returns:
            Dictionary with metrics
        """
        logger.info("Training Isolation Forest...")
        
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42,
            n_jobs=-1
        )
        
        # Fit
        self.model.fit(X)
        
        # Get anomaly scores (negative because of sklearn convention)
        anomaly_scores = -self.model.score_samples(X)
        self.reconstruction_errors_train = anomaly_scores
        
        logger.info(f"Isolation Forest trained. Mean anomaly score: {anomaly_scores.mean():.4f}")
        
        return {'mean_score': anomaly_scores.mean(), 'std_score': anomaly_scores.std()}
    
    def set_threshold(self, method: str = 'percentile', percentile: float = 95,
                     multiplier: float = 1.5):
        """
        Set anomaly detection threshold.
        
        Args:
            method: 'percentile' or 'iqr'
            percentile: Percentile for threshold (if method='percentile')
            multiplier: IQR multiplier (if method='iqr')
        """
        if self.reconstruction_errors_train is None:
            raise ValueError("Train model first")
        
        if method == 'percentile':
            self.threshold = np.percentile(self.reconstruction_errors_train, percentile)
            logger.info(f"Threshold set to {percentile}th percentile: {self.threshold:.4f}")
        elif method == 'iqr':
            Q1 = np.percentile(self.reconstruction_errors_train, 25)
            Q3 = np.percentile(self.reconstruction_errors_train, 75)
            IQR = Q3 - Q1
            self.threshold = Q3 + multiplier * IQR
            logger.info(f"Threshold set using IQR method: {self.threshold:.4f}")
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def detect_anomalies(self, X: np.ndarray, return_scores: bool = True) -> Tuple[
        np.ndarray, np.ndarray]:
        """
        Detect anomalies.
        
        Args:
            X: Data to evaluate
            return_scores: Whether to return anomaly scores
        
        Returns:
            Tuple of (is_anomaly, scores)
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        if self.model_type == 'autoencoder':
            X_scaled = self.scaler.transform(X)
            X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(self.device)
            
            self.model.eval()
            with torch.no_grad():
                X_recon, _ = self.model(X_tensor)
                scores = torch.mean((X_tensor - X_recon) ** 2, dim=1).cpu().numpy()
        else:  # isolation_forest
            scores = -self.model.score_samples(X)
        
        if self.threshold is None:
            self.set_threshold()
        
        is_anomaly = scores > self.threshold
        
        if return_scores:
            return is_anomaly, scores
        else:
            return is_anomaly
    
    def save_model(self, path: str = "models/autoencoder.pth"):
        """Save trained model."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        if self.model_type == 'autoencoder':
            torch.save(self.model.state_dict(), path)
        else:
            joblib.dump(self.model, path)
        
        # Save metadata
        metadata = {
            'scaler': self.scaler,
            'threshold': self.threshold,
            'model_type': self.model_type,
            'feature_names': self.feature_names
        }
        meta_path = path.replace('.pth', '_meta.joblib').replace('.joblib', '_meta.joblib')
        joblib.dump(metadata, meta_path)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str = "models/autoencoder.pth", n_features: int = None):
        """Load trained model."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        if self.model_type == 'autoencoder':
            if n_features is None:
                raise ValueError("n_features required for autoencoder")
            
            self.model = Autoencoder(n_features).to(self.device)
            self.model.load_state_dict(torch.load(path, map_location=self.device))
            self.model.eval()
        else:
            self.model = joblib.load(path)
        
        # Load metadata
        meta_path = path.replace('.pth', '_meta.joblib').replace('.joblib', '_meta.joblib')
        if Path(meta_path).exists():
            metadata = joblib.load(meta_path)
            self.scaler = metadata.get('scaler', self.scaler)
            self.threshold = metadata.get('threshold', self.threshold)
            self.feature_names = metadata.get('feature_names')
        
        logger.info(f"Model loaded from {path}")


def train_and_save_anomaly_detectors(data_path: str, output_dir: str = "models/"):
    """Train and save both autoencoder and isolation forest - main entry point."""
    logger.info("Training anomaly detectors...")
    
    # Load normal data
    X = pd.read_csv(data_path).values
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Train autoencoder
    ae_detector = AnomalyDetector(model_type='autoencoder', device='cuda' if torch.cuda.is_available() else 'cpu')
    ae_detector.train_autoencoder(X, epochs=50, batch_size=128, learning_rate=0.001)
    ae_detector.set_threshold(method='percentile', percentile=95)
    ae_detector.save_model(f"{output_dir}autoencoder.pth")
    
    # Train Isolation Forest
    if_detector = AnomalyDetector(model_type='isolation_forest')
    if_detector.train_isolation_forest(X, contamination=0.05, n_estimators=100)
    if_detector.set_threshold(method='iqr')
    if_detector.save_model(f"{output_dir}isolation_forest.joblib")
    
    logger.info("Anomaly detectors saved")
    return ae_detector, if_detector


if __name__ == "__main__":
    ae_detector, if_detector = train_and_save_anomaly_detectors("data/processed/train_normal.csv")
    logger.info("Training complete")
