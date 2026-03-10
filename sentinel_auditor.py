"""
Sentinel Auditor Agent
Monitors core metrics, identifies deficits, publishes Task Proposals
Implements Cycle 1: API Latency Monitoring
"""
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from firebase_foundry_config import get_firebase_instance, TaskProposal

logger = logging.getLogger(__name__)

class SentinelAuditor:
    """Primary monitoring agent for the cognitive kernel"""
    
    def __init__(self, check_interval: int = 60):
        """Initialize with monitoring interval in seconds"""
        self.check_interval = check_interval
        self.firebase = get_firebase_instance()
        self.metrics_history = {}  # Track metric history for anomaly detection
        
        # Threshold configurations (would come from config in production)
        self.thresholds = {
            '/api/v1/users': {
                'p95_latency_ms': 400,
                'error_rate': 0.01,
                'consecutive_violations': 3
            }
        }
        
        logger.info(f"Sentinel Auditor initialized with {check_interval}s check interval")
    
    def simulate_metric_collection(self, endpoint: str) -> Dict[str, float]:
        """
        Simulate metric collection from Prometheus/Cloud Monitoring
        In production, this would query actual monitoring systems
        """
        # Simulate realistic latency with occasional spikes
        base_latency = random.uniform(150, 350)
        spike_chance = random.random()
        
        if spike_chance < 0.1:  # 10% chance of latency spike
            latency = random.uniform(400, 800)
            logger.warning(f"Simulated latency spike on {endpoint}: {latency:.1f}ms")
        else:
            latency = base_latency
        
        # Simulate error rate
        error_rate = random.uniform(0.001, 0.02)
        
        return {
            'p95_latency_ms': latency,
            'error_rate': error_rate,
            'request_count': random.randint(100, 1000),
            'timestamp': datetime.now()
        }
    
    def check_constitution_compliance(self, metrics: Dict) -> List[str]:
        """Check metrics against Non-Degradation Principle"""
        violations = []
        
        # Check error rate degradation
        if metrics.get('error_rate', 0) > 0.01:  # 1% threshold
            violations.append(f"Error rate {metrics['error_rate']:.3%} exceeds 1% threshold")
        
        # Check for data loss indicators (simulated)
        if random.random() < 0.05:  # 5% chance to simulate data loss alert
            violations.append("Potential data deletion detected in audit logs")
        
        return violations
    
    def detect_deficit(self, endpoint: str, metrics: Dict) -> Optional[Dict]:
        """
        Detect if metrics indicate a skill deficit requiring intervention
        Returns task proposal if deficit detected, None otherwise
        """
        # Initialize history tracking for this endpoint
        if endpoint not in self.metrics_history:
            self.metrics_history[endpoint] = []
        
        # Add current metrics to history
        self.metrics_history[endpoint].append(metrics)
        
        # Keep only last 10 readings
        if len(self.metrics_history[endpoint]) > 10:
            self.metrics_history[endpoint] = self.metrics_history[endpoint][-10:]
        
        # Check against thresholds
        threshold = self.thresholds.get(endpoint, {})
        if not threshold:
            logger.warning(f"No thresholds defined for {endpoint}")
            return None
        
        # Check consecutive violations
        consecutive_violations = 0
        for historic_metric in self.metrics_history[endpoint][-threshold['consecutive_violations']:]:
            if historic_metric['p95_latency_ms'] > threshold['p95_latency_ms']:
                consecutive_violations += 1
        
        if consecutive_violations >= threshold['consecutive_violations']:
            # Constitution check
            violations = self.check_constitution_compliance(metrics)
            if violations:
                logger.error(f"Constitution violations prevent task creation: {violations}")
                self.firebase.log_constitution_event(
                    'deficit_detected_with_violations',
                    {'endpoint': endpoint, 'violations': violations}
                )
                return None
            
            # Create task proposal
            task_proposal = {
                'target_metric': 'p95_latency_ms',
                'current_value': metrics['p95_latency_ms'],
                'goal_value': 200,  # Target improvement
                'status': 'pending',
                'endpoint': endpoint,
                'constraints': {
                    'max_error_rate_increase': 0.001,
                    'no_data_loss': True,
                    'observability_maintained': True
                },
                'metadata': {
                    'detection_method': 'consecutive_threshold_violation',
                    'historical_samples': len(self.metrics_history[endpoint]),
                    'consecutive_violations': consecutive_violations
                }
            }
            
            logger.info(f"Deficit detected on {endpoint}: {metrics['p95_latency_ms']:.1f}ms > {threshold['p95_latency_ms']}ms threshold")
            return task_proposal
        
        return None
    
    def monitor_cycle(self):
        """Execute one monitoring cycle"""
        logger.info("Starting Sentinel Auditor monitoring cycle")
        
        endpoints = ['/api/v1/users', '/api/v1/products', '/api/v1/orders']  # Simulated endpoints
        
        for endpoint in endpoints:
            try:
                # Collect metrics
                metrics = self.simulate_metric_collection(endpoint)
                
                # Detect deficit
                task_proposal = self.detect_deficit(endpoint, metrics)
                
                if task_proposal:
                    # Submit task to Firestore
                    task_id = self.firebase.create_task(task_proposal)
                    
                    # Log for transparency
                    self.firebase.log_constitution_event(
                        'task_created',
                        {
                            'endpoint': endpoint,
                            'current_latency': metrics['p95_latency_ms'],
                            'goal_latency': 200
                        },
                        task_id
                    )
                    
                    logger.info(f"Task {task_id} created for {endpoint} latency optimization")
                
            except Exception as e:
                logger.error(f"Error monitoring {endpoint}: {e}", exc_info=True)
                self.firebase.log_constitution_event(
                    'monitoring_error',
                    {'endpoint': endpoint, 'error': str(e)}
                )
    
    def run_continuously(self):
        """Main monitoring loop"""
        logger.info("Starting Sentinel Auditor continuous monitoring")
        
        try:
            while True:
                start_time = time.time()
                self.monitor_cycle()
                
                # Calculate sleep time to maintain exact interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.check_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Sent