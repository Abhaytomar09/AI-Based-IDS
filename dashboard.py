"""
Streamlit dashboard for IDS monitoring and alerting
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

from src.inference import get_inference_engine
from src.utils import load_alerts
from src.constants import ATTACK_TYPES, ALERT_COLORS

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="IDS Monitoring Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-critical {
        background-color: #fee;
        border-left: 4px solid #c00;
    }
    .alert-warning {
        background-color: #fef3cd;
        border-left: 4px solid #ffc107;
    }
    .metric-card {
        text-align: center;
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Page title
st.title("🛡️ AI-Powered IDS Monitoring Dashboard")
st.markdown("Real-time network intrusion detection with ML/DL hybrid approach")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    page = st.radio(
        "Select Page",
        ["📊 Overview", "🔔 Alerts", "🔍 Inference", "📈 Analytics", "ℹ️ About"]
    )
    
    st.markdown("---")
    
    st.subheader("Model Settings")
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.6, 0.05)
    anomaly_threshold = st.slider("Anomaly Threshold", 0.0, 5.0, 2.5, 0.25)


# Load data
@st.cache_resource
def get_inference_engine_cached():
    return get_inference_engine()


@st.cache_data
def load_alerts_data():
    return load_alerts("alerts.jsonl")


# Pages
if page == "📊 Overview":
    st.header("Dashboard Overview")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    alerts = load_alerts_data()
    
    with col1:
        st.metric("Total Alerts", len(alerts), "⚠️")
    
    with col2:
        if alerts:
            alert_types = [a.get('alert_type') for a in alerts]
            most_common = max(set(alert_types), key=alert_types.count)
            st.metric("Most Common Alert", most_common)
        else:
            st.metric("Most Common Alert", "N/A")
    
    with col3:
        if alerts:
            avg_confidence = np.mean([a.get('confidence', 0) for a in alerts])
            st.metric("Avg Confidence", f"{avg_confidence:.2%}")
        else:
            st.metric("Avg Confidence", "N/A")
    
    with col4:
        st.metric("System Status", "🟢 Healthy", "Operational")
    
    st.markdown("---")
    
    # Alert distribution
    if alerts:
        col1, col2 = st.columns(2)
        
        with col1:
            alert_types = [a.get('alert_type', 'Unknown') for a in alerts]
            alert_counts = pd.Series(alert_types).value_counts()
            
            fig = px.pie(
                values=alert_counts.values,
                names=alert_counts.index,
                title="Alert Distribution by Type",
                color_discrete_map=ALERT_COLORS
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Timeline
            timestamps = [datetime.fromisoformat(a['timestamp']) for a in alerts]
            df_timeline = pd.DataFrame({
                'timestamp': timestamps,
                'hour': [t.hour for t in timestamps]
            })
            
            hourly_counts = df_timeline.groupby('hour').size()
            
            fig = px.bar(
                x=hourly_counts.index,
                y=hourly_counts.values,
                title="Alerts Over Time",
                labels={'x': 'Hour', 'y': 'Alert Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No alerts yet. System is monitoring...")


elif page == "🔔 Alerts":
    st.header("Recent Alerts")
    
    alerts = load_alerts_data()
    
    if not alerts:
        st.info("✅ No alerts detected")
    else:
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alert_types = list(set(a.get('alert_type') for a in alerts))
            selected_type = st.multiselect("Filter by Type", alert_types, default=alert_types)
        
        with col2:
            min_conf = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.05)
        
        with col3:
            st.markdown("")  # Spacing
        
        # Filter alerts
        filtered_alerts = [
            a for a in alerts 
            if a.get('alert_type') in selected_type and a.get('confidence', 0) >= min_conf
        ]
        
        st.markdown(f"Showing {len(filtered_alerts)} of {len(alerts)} alerts")
        
        # Display alerts
        for alert in reversed(filtered_alerts[-20:]):  # Show latest 20
            severity = "🔴 Critical" if alert['confidence'] > 0.9 else "🟠 Warning"
            
            with st.expander(
                f"{severity} | {alert['alert_type']} | {alert['flow_id']} | {alert['confidence']:.2%}"
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Timestamp**: {alert['timestamp']}")
                    st.write(f"**Alert Type**: {alert['alert_type']}")
                    st.write(f"**Confidence**: {alert['confidence']:.2%}")
                    st.write(f"**Anomaly Score**: {alert['anomaly_score']:.4f}")
                
                with col2:
                    st.write("**Top Contributing Features**:")
                    for feat in alert.get('top_features', [])[:5]:
                        st.write(f"  • {feat['feature']}: {feat['impact']:.1%}")
                
                st.write(f"**Recommended Action**: {alert.get('recommended_action', 'Review')}")
                
                with st.expander("Flow Context"):
                    st.json(alert.get('flow_context', {}))


elif page == "🔍 Inference":
    st.header("Real-time Inference")
    
    engine = get_inference_engine_cached()
    
    st.markdown("### Input Network Flow")
    
    col1, col2 = st.columns(2)
    
    with col1:
        src_ip = st.text_input("Source IP", "192.168.1.100")
        src_port = st.number_input("Source Port", min_value=1, max_value=65535, value=12345)
        duration = st.number_input("Duration (s)", min_value=0.0, value=10.5, step=0.1)
        src_bytes = st.number_input("Source Bytes", min_value=0, value=1024, step=100)
    
    with col2:
        dst_ip = st.text_input("Destination IP", "10.0.0.5")
        dst_port = st.number_input("Destination Port", min_value=1, max_value=65535, value=80)
        protocol = st.selectbox("Protocol", ["TCP", "UDP", "ICMP"])
        dst_bytes = st.number_input("Destination Bytes", min_value=0, value=512, step=100)
    
    if st.button("🔍 Analyze Flow", type="primary"):
        flow_data = {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'src_port': src_port,
            'dst_port': dst_port,
            'protocol': protocol,
            'duration': duration,
            'src_bytes': src_bytes,
            'dst_bytes': dst_bytes,
            'num_packets': int(duration * 5),  # Estimate
        }
        
        try:
            result = engine.predict(flow_data, 
                                   confidence_threshold=confidence_threshold,
                                   anomaly_threshold=anomaly_threshold)
            
            st.markdown("### Prediction Result")
            
            if result.get('alert'):
                alert = result['alert']
                st.error(f"🚨 **ALERT TRIGGERED: {alert['alert_type']}**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Confidence", f"{alert['confidence']:.2%}")
                with col2:
                    st.metric("Anomaly Score", f"{alert['anomaly_score']:.4f}")
                with col3:
                    st.metric("Action", alert.get('recommended_action', 'Review'))
                
                st.info(f"**Reasoning**: {', '.join([f['feature'] for f in alert['top_features'][:3]])}")
            else:
                st.success("✅ **NO THREAT DETECTED**")
            
            # Model details
            with st.expander("Model Details"):
                models = result.get('models', {})
                
                if 'supervised' in models:
                    sup = models['supervised']
                    st.write(f"**Supervised Model Confidence**: {sup['confidence']:.2%}")
                
                if 'anomaly' in models:
                    anom = models['anomaly']
                    st.write(f"**Anomaly Score**: {anom['score']:.4f}")
                    st.write(f"**Is Anomaly**: {'Yes' if anom['is_anomaly'] else 'No'}")
        
        except Exception as e:
            st.error(f"Error during inference: {e}")


elif page == "📈 Analytics":
    st.header("Analytics & Statistics")
    
    alerts = load_alerts_data()
    
    if not alerts:
        st.info("No alerts to analyze yet")
    else:
        # Convert to DataFrame
        df_alerts = pd.DataFrame(alerts)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Confidence Distribution")
            
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=df_alerts['confidence'],
                nbinsx=20,
                name='Confidence'
            ))
            fig.update_layout(title="Alert Confidence Distribution", xaxis_title="Confidence")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Top Source IPs")
            
            src_ips = []
            for alert in alerts:
                src_ip = alert.get('flow_context', {}).get('src_ip')
                if src_ip:
                    src_ips.append(src_ip)
            
            if src_ips:
                ip_counts = pd.Series(src_ips).value_counts().head(10)
                fig = px.bar(
                    x=ip_counts.index,
                    y=ip_counts.values,
                    title="Top 10 Source IPs",
                    labels={'x': 'Source IP', 'y': 'Alert Count'}
                )
                st.plotly_chart(fig, use_container_width=True)


elif page == "ℹ️ About":
    st.header("About This System")
    
    st.markdown("""
    ### AI-Powered Intrusion Detection System (IDS)
    
    This system combines Machine Learning and Deep Learning to detect network intrusions in real-time.
    
    #### Key Features
    - **Hybrid Approach**: Supervised + Unsupervised learning models
    - **Real-time Detection**: Process network flows in real-time
    - **Explainability**: SHAP-based feature importance
    - **Continuous Learning**: Adapts to new threats
    
    #### Models
    - **XGBoost**: For known attack classification
    - **Autoencoder**: For anomaly detection (zero-day)
    - **Isolation Forest**: Complementary anomaly detection
    
    #### Architecture
    ```
    Network Flows → Preprocessing → Feature Engineering → 
    Supervised Model + Unsupervised Model → Ensemble Decision → Alerts
    ```
    
    #### Performance Targets
    - F1-Score: > 0.90 on known attacks
    - TPR @ 1% FPR: > 0.85 on anomalies
    - Latency: < 50ms per flow (CPU)
    - Throughput: > 10,000 flows/sec
    
    #### Technologies
    - **ML/DL**: XGBoost, PyTorch, scikit-learn
    - **Streaming**: Kafka, FastAPI
    - **Visualization**: Streamlit, Plotly
    - **Explainability**: SHAP, LIME
    """)
    
    st.markdown("---")
    st.markdown("📚 **Documentation**: Check README.md for full setup and usage instructions")


# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "IDS Dashboard | Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") +
    " | Status: 🟢 Active"
    "</div>",
    unsafe_allow_html=True
)
