"""
Kafka consumer for real-time anomaly detection
"""
import json
import logging
import argparse
from kafka import KafkaConsumer
from datetime import datetime
import time

from src.inference import get_inference_engine
from src.utils import save_alert

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class KafkaFlowConsumer:
    """Consume network flows and run real-time detection."""
    
    def __init__(self, broker: str = 'localhost:9092', topic: str = 'network_flows',
                 group_id: str = 'ids_detector'):
        """
        Initialize consumer.
        
        Args:
            broker: Kafka broker address
            topic: Kafka topic name
            group_id: Consumer group ID
        """
        self.topic = topic
        self.group_id = group_id
        
        try:
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=broker,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info(f"Connected to Kafka broker: {broker}, topic: {topic}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
        
        # Initialize inference engine
        self.engine = get_inference_engine()
        self.stats = {
            'total_flows': 0,
            'alerts': 0,
            'start_time': datetime.utcnow()
        }
    
    def process_flow(self, flow_data: dict) -> dict:
        """
        Process single flow through detection pipeline.
        
        Args:
            flow_data: Network flow data
        
        Returns:
            Detection result
        """
        try:
            result = self.engine.predict(flow_data)
            
            self.stats['total_flows'] += 1
            
            if result.get('alert'):
                self.stats['alerts'] += 1
                save_alert(result['alert'])
                
                # Log alert
                alert = result['alert']
                logger.warning(
                    f"🚨 ALERT: {alert['alert_type']} detected from {alert['flow_id']} "
                    f"(confidence: {alert['confidence']:.2%})"
                )
                
                return result
            
            if self.stats['total_flows'] % 100 == 0:
                logger.info(f"Processed {self.stats['total_flows']} flows, "
                          f"{self.stats['alerts']} alerts")
            
            return None
        
        except Exception as e:
            logger.error(f"Error processing flow: {e}")
            return None
    
    def start(self, timeout_ms: int = 1000):
        """
        Start consuming and processing flows.
        
        Args:
            timeout_ms: Message poll timeout in milliseconds
        """
        logger.info(f"Starting consumer for topic: {self.topic}")
        
        try:
            for message in self.consumer:
                flow_data = message.value
                self.process_flow(flow_data)
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        
        finally:
            self.consumer.close()
            elapsed = (datetime.utcnow() - self.stats['start_time']).total_seconds()
            
            logger.info(f"Consumer stopped")
            logger.info(f"Statistics:")
            logger.info(f"  Total flows: {self.stats['total_flows']}")
            logger.info(f"  Alerts: {self.stats['alerts']}")
            logger.info(f"  Alert rate: {self.stats['alerts']/max(self.stats['total_flows'], 1)*100:.2f}%")
            logger.info(f"  Elapsed time: {elapsed:.1f}s")
            if elapsed > 0:
                logger.info(f"  Throughput: {self.stats['total_flows']/elapsed:.1f} flows/sec")


def main():
    parser = argparse.ArgumentParser(description="Kafka consumer for IDS detection")
    parser.add_argument('--broker', type=str, default='localhost:9092', help='Kafka broker')
    parser.add_argument('--topic', type=str, default='network_flows', help='Kafka topic')
    parser.add_argument('--group', type=str, default='ids_detector', help='Consumer group')
    
    args = parser.parse_args()
    
    consumer = KafkaFlowConsumer(broker=args.broker, topic=args.topic, group_id=args.group)
    consumer.start()


if __name__ == "__main__":
    main()
