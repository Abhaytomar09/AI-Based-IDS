"""
Kafka producer for streaming network flow data
"""
import pandas as pd
import json
import time
import logging
import argparse
from kafka import KafkaProducer
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class KafkaFlowProducer:
    """Produce network flow data to Kafka topic."""
    
    def __init__(self, broker: str = 'localhost:9092', topic: str = 'network_flows'):
        """
        Initialize producer.
        
        Args:
            broker: Kafka broker address
            topic: Kafka topic name
        """
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=broker,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )
        logger.info(f"Connected to Kafka broker: {broker}")
    
    def send_flow(self, flow_data: dict, key: str = None):
        """
        Send single flow to Kafka.
        
        Args:
            flow_data: Flow data dictionary
            key: Optional partition key
        """
        try:
            future = self.producer.send(self.topic, value=flow_data, key=key.encode() if key else None)
            record_metadata = future.get(timeout=10)
            logger.debug(f"Sent flow to {record_metadata.topic} partition {record_metadata.partition}")
        except Exception as e:
            logger.error(f"Error sending flow: {e}")
    
    def produce_from_csv(self, csv_path: str, speed_factor: float = 1.0, 
                        batch_size: int = 1, max_flows: int = None):
        """
        Produce flows from CSV file.
        
        Args:
            csv_path: Path to CSV file
            speed_factor: Speed multiplier (1.0 = original speed)
            batch_size: Number of flows to send together
            max_flows: Maximum flows to send
        """
        logger.info(f"Loading flows from {csv_path}")
        
        df = pd.read_csv(csv_path)
        
        if max_flows:
            df = df.head(max_flows)
        
        logger.info(f"Producing {len(df)} flows with speed factor {speed_factor}")
        
        for idx, row in df.iterrows():
            flow_data = row.to_dict()
            
            # Use flow identifier as key for partitioning
            flow_key = f"{flow_data.get('src_ip', '')}:{flow_data.get('dst_ip', '')}"
            
            self.send_flow(flow_data, key=flow_key)
            
            if (idx + 1) % batch_size == 0:
                logger.info(f"Produced {idx + 1} flows")
            
            # Simulate delay based on duration if available
            if 'duration' in flow_data and speed_factor > 0:
                delay = float(flow_data['duration']) / speed_factor
                time.sleep(min(delay, 1.0))  # Cap delay at 1 second
        
        logger.info("Production complete")
        self.producer.close()


def main():
    parser = argparse.ArgumentParser(description="Kafka producer for IDS flows")
    parser.add_argument('--data', type=str, required=True, help='CSV file path')
    parser.add_argument('--broker', type=str, default='localhost:9092', help='Kafka broker')
    parser.add_argument('--topic', type=str, default='network_flows', help='Kafka topic')
    parser.add_argument('--speed', type=float, default=1.0, help='Speed factor')
    parser.add_argument('--max-flows', type=int, default=None, help='Max flows to send')
    
    args = parser.parse_args()
    
    producer = KafkaFlowProducer(broker=args.broker, topic=args.topic)
    producer.produce_from_csv(args.data, speed_factor=args.speed, max_flows=args.max_flows)


if __name__ == "__main__":
    main()
