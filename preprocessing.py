"""
Data preprocessing and feature engineering module
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Handle data loading, cleaning, and feature engineering."""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.feature_names = None
        self.categorical_features = []
        self.numerical_features = []
        
    def load_data(self, path: str) -> pd.DataFrame:
        """Load dataset from CSV."""
        logger.info(f"Loading data from {path}")
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        return df
    
    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'fill') -> pd.DataFrame:
        """Handle missing values in dataset."""
        logger.info(f"Handling missing values (strategy: {strategy})")
        df = df.copy()
        
        missing_count = df.isnull().sum()
        if missing_count.sum() > 0:
            logger.warning(f"Missing values found:\n{missing_count[missing_count > 0]}")
            
            if strategy == 'fill':
                # Fill numerical with median, categorical with mode
                for col in df.columns:
                    if df[col].isnull().sum() > 0:
                        if df[col].dtype in ['float64', 'int64']:
                            df[col].fillna(df[col].median(), inplace=True)
                        else:
                            df[col].fillna(df[col].mode()[0], inplace=True)
            elif strategy == 'drop':
                df = df.dropna()
        
        logger.info(f"After handling missing values: {len(df)} rows")
        return df
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows."""
        initial_len = len(df)
        df = df.drop_duplicates()
        logger.info(f"Removed {initial_len - len(df)} duplicate rows")
        return df
    
    def handle_outliers(self, df: pd.DataFrame, columns: List[str] = None, 
                        method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:
        """Handle outliers using IQR or Z-score method."""
        logger.info(f"Handling outliers (method: {method}, threshold: {threshold})")
        df = df.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns
        
        if method == 'iqr':
            for col in columns:
                # Only process numeric columns
                if df[col].dtype in ['float64', 'float32', 'int64', 'int32', 'int16', 'int8', 'uint64', 'uint32', 'uint16', 'uint8']:
                    Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
        
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        logger.info(f"After outlier removal: {len(df)} rows")
        return df
    
    def encode_categorical(self, df: pd.DataFrame, categorical_cols: List[str] = None,
                          method: str = 'onehot') -> pd.DataFrame:
        """Encode categorical features."""
        logger.info(f"Encoding categorical features (method: {method})")
        df = df.copy()
        
        if categorical_cols is None:
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        self.categorical_features = categorical_cols
        
        if method == 'onehot':
            df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
            logger.info(f"One-hot encoding created {len(df.columns)} total features")
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create new features from existing ones."""
        logger.info("Engineering features...")
        df = df.copy()
        
        # Flow-based features
        if 'src_bytes' in df.columns and 'dst_bytes' in df.columns:
            df['total_bytes'] = df['src_bytes'] + df['dst_bytes']
            df['src_dst_byte_ratio'] = df['src_bytes'] / (df['dst_bytes'] + 1)
        
        # Rate features
        if 'duration' in df.columns and 'src_bytes' in df.columns:
            df['bytes_per_sec'] = df['src_bytes'] / (df['duration'] + 1)
        
        if 'duration' in df.columns and 'dst_bytes' in df.columns:
            df['dst_bytes_per_sec'] = df['dst_bytes'] / (df['duration'] + 1)
        
        if 'num_packets' in df.columns and 'duration' in df.columns:
            df['packets_per_sec'] = df['num_packets'] / (df['duration'] + 1)
        
        if 'src_bytes' in df.columns and 'num_packets' in df.columns:
            df['bytes_per_packet'] = df['src_bytes'] / (df['num_packets'] + 1)
        
        # Flag features (if available)
        flag_columns = [col for col in df.columns if 'flag' in col.lower()]
        if flag_columns:
            df['num_flags'] = df[flag_columns].sum(axis=1)
        
        # Service features (if available)
        service_columns = [col for col in df.columns if 'service' in col.lower()]
        if service_columns:
            df['num_services'] = df[service_columns].sum(axis=1)
        
        logger.info(f"Feature engineering created {len(df.columns)} total features")
        return df
    
    def prepare_data(self, df: pd.DataFrame, label_col: str = 'label',
                    test_size: float = 0.2, stratify: bool = True) -> Tuple[
                        pd.DataFrame, pd.DataFrame, List[str]]:
        """Complete preprocessing pipeline."""
        # Clean data
        df = self.handle_missing_values(df)
        df = self.remove_duplicates(df)
        
        # Handle outliers (except for label column)
        feature_cols = [col for col in df.columns if col != label_col]
        
        # Only handle outliers on numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            df = self.handle_outliers(df, columns=numeric_cols)
        # Encode categorical
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        if label_col in categorical_cols:
            categorical_cols.remove(label_col)
        
        if categorical_cols:
            df = self.encode_categorical(df, categorical_cols)
        
        # Feature engineering
        df = self.engineer_features(df)
        
        # Train-test split
        feature_cols = [col for col in df.columns if col != label_col]
        self.feature_names = feature_cols
        
        if stratify and label_col in df.columns:
            X_train, X_test, y_train, y_test = train_test_split(
                df[feature_cols],
                df[label_col],
                test_size=test_size,
                random_state=self.random_state,
                stratify=df[label_col]
            )
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                df[feature_cols],
                df[label_col] if label_col in df.columns else None,
                test_size=test_size,
                random_state=self.random_state
            )
        
        train_df = X_train.copy()
        test_df = X_test.copy()
        if label_col in df.columns:
            train_df[label_col] = y_train.values
            test_df[label_col] = y_test.values
        
        logger.info(f"Train set: {len(train_df)}, Test set: {len(test_df)}")
        return train_df, test_df, feature_cols
    
    def scale_features(self, train_df: pd.DataFrame, test_df: pd.DataFrame,
                      feature_cols: List[str], fit: bool = True) -> Tuple[
                          pd.DataFrame, pd.DataFrame]:
        """Standardize numerical features."""
        logger.info("Scaling features...")
        
        train_df = train_df.copy()
        test_df = test_df.copy()
        
        if fit:
            train_df[feature_cols] = self.scaler.fit_transform(train_df[feature_cols])
        else:
            train_df[feature_cols] = self.scaler.transform(train_df[feature_cols])
        
        test_df[feature_cols] = self.scaler.transform(test_df[feature_cols])
        
        return train_df, test_df
    
    def save_scaler(self, path: str = "models/scaler.joblib"):
        """Save fitted scaler."""
        joblib.dump(self.scaler, path)
        logger.info(f"Scaler saved to {path}")
    
    def load_scaler(self, path: str = "models/scaler.joblib"):
        """Load fitted scaler."""
        self.scaler = joblib.load(path)
        logger.info(f"Scaler loaded from {path}")


def load_and_preprocess(
    data_path: str,
    output_dir: str = "data/processed/",
    label_col: str = "label",
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Complete preprocessing pipeline - main entry point.
    
    Args:
        data_path: Path to raw CSV file
        output_dir: Directory to save processed files
        label_col: Name of label column
        test_size: Proportion of test set
    
    Returns:
        Dictionary with train_df, test_df, feature_cols, normal_df
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    preprocessor = DataPreprocessor()
    
    # Load and prepare
    df = preprocessor.load_data(data_path)
    train_df, test_df, feature_cols = preprocessor.prepare_data(
        df, label_col=label_col, test_size=test_size
    )
    
    # Scale
    train_df, test_df = preprocessor.scale_features(train_df, test_df, feature_cols)
    preprocessor.save_scaler(f"{output_dir}scaler.joblib")
    
    # Save datasets
    train_df.to_csv(f"{output_dir}train.csv", index=False)
    test_df.to_csv(f"{output_dir}test.csv", index=False)
    
    # Save normal data (for unsupervised training)
    if label_col in train_df.columns:
        normal_df = train_df[train_df[label_col] == 'Normal'].drop(columns=[label_col])
        normal_df.to_csv(f"{output_dir}train_normal.csv", index=False)
        logger.info(f"Saved {len(normal_df)} normal samples for unsupervised training")
    
    # Save feature names
    joblib.dump(feature_cols, f"{output_dir}feature_names.joblib")
    
    logger.info(f"Preprocessing complete. Files saved to {output_dir}")
    
    return {
        'train_df': train_df,
        'test_df': test_df,
        'feature_cols': feature_cols,
        'preprocessor': preprocessor
    }


if __name__ == "__main__":
    # Example usage
    result = load_and_preprocess(
        "data/raw/NSL-KDD-train.csv",
        "data/processed/"
    )
    print(f"Train shape: {result['train_df'].shape}")
    print(f"Test shape: {result['test_df'].shape}")
