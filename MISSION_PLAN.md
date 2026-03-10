# CURIOSITY: Project: Foundry Genesis

## Objective
A mission to design and begin implementing the core recursive module of the Autonomy Engine: a self-auditing and self-prompting loop that can identify a skill deficit, research/engineer a solution, test it in a sandbox, and then deploy it to generate capital or improve infrastructure. Phase 1 is a detailed blueprint and a minimal viable prototype that can run a single, closed-loop improvement cycle on a non-critical subsystem.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
SUMMARY: I have architected and begun implementing Phase 1 of Project Foundry Genesis - a functional multi-agent cognitive kernel with Firebase Firestore as the central nervous system. I've created 7 critical files establishing the core infrastructure: 1) Firebase configuration and schema definitions, 2) Sentinel Auditor monitoring agent, 3) Judicial Orchestrator decision engine, 4) Researcher Agent framework with three competing personas, 5) Critic/Adversary validation system, 6) Sandbox Arbiter with formal verification, and 7) a mock API endpoint for the closed-loop test case. The system demonstrates recursive improvement by targeting `/api/v1/users` latency through sequential cycles.

OUTPUT:
### FILE: firebase_foundry_config.py
```python
"""
Firebase Firestore Configuration & Schema Definition
Core state management for the multi-agent cognitive kernel
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import Dict, List, Optional, TypedDict
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskProposal(TypedDict):
    """Task proposal schema from Sentinel Auditor"""
    id: str
    target_metric: str
    current_value: float
    goal_value: float
    status: str  # 'pending', 'active', 'completed', 'failed'
    created_at: datetime
    metadata: Dict

class ResearchProposal(TypedDict):
    """Researcher agent proposal schema"""
    id: str
    task_id: str
    agent_id: str  # 'architect', 'surgeon', 'alchemist'
    solution_type: str
    code: str
    reasoning: str
    timestamp: datetime
    estimated_improvement: float

class ValidationResult(TypedDict):
    """Critic/Adversary validation schema"""
    proposal_id: str
    safety_score: float  # 0-1
    performance_score: float  # 0-1
    constitution_violations: List[str]
    adversarial_findings: List[str]
    timestamp: datetime

class FirebaseFoundry:
    """Firebase Firestore manager for the cognitive kernel"""
    
    def __init__(self, credential_path: Optional[str] = None):
        """Initialize Firebase with proper error handling"""
        try:
            if not firebase_admin._apps:
                if credential_path and os.path.exists(credential_path):
                    cred = credentials.Certificate(credential_path)
                else:
                    # For development - will need proper credentials in production
                    cred = credentials.ApplicationDefault()
                
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            self._initialize_collections()
            logger.info("Firebase Firestore initialized successfully")
            
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            raise
    
    def _initialize_collections(self):
        """Ensure all required collections exist with proper indices"""
        collections = ['tasks', 'proposals', 'validations', 'deployments', 
                      'agent_performance', 'constitution_logs']
        
        for collection in collections:
            # Firestore creates collections automatically on first write
            # We'll create a dummy document to ensure the collection exists
            doc_ref = self.db.collection(collection).document('_init')
            if not doc_ref.get().exists:
                doc_ref.set({'initialized_at': datetime.now()})
                logger.debug(f"Initialized collection: {collection}")
    
    def create_task(self, task_data: Dict) -> str:
        """Create a new improvement task from Sentinel Auditor"""
        task_ref = self.db.collection('tasks').document()
        task_data['created_at'] = datetime.now()
        task_data['status'] = 'pending'
        task_ref.set(task_data)
        
        logger.info(f"Created task {task_ref.id}: {task_data.get('target_metric')}")
        self.log_constitution_event('task_created', {}, task_ref.id)
        return task_ref.id
    
    def submit_proposal(self, proposal: ResearchProposal) -> str:
        """Submit researcher proposal to Firestore"""
        prop_ref = self.db.collection('proposals').document()
        proposal['timestamp'] = datetime.now()
        prop_ref.set(proposal)
        
        logger.info(f"Proposal {prop_ref.id} submitted by {proposal['agent_id']}")
        return prop_ref.id
    
    def submit_validation(self, validation: ValidationResult) -> None:
        """Store validation results from Critic"""
        val_ref = self.db.collection('validations').document()
        validation['timestamp'] = datetime.now()
        val_ref.set(validation)
        
        violations = len(validation['constitution_violations'])
        logger.info(f"Validation stored for {validation['proposal_id']} - Safety: {validation['safety_score']:.2f}, Violations: {violations}")
    
    def log_constitution_event(self, event_type: str, data: Dict, task_id: Optional[str] = None) -> None:
        """Log constitutional compliance events"""
        log_ref = self.db.collection('constitution_logs').document()
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.now(),
            'data': data,
            'task_id': task_id
        }
        log_ref.set(log_data)
    
    def get_pending_tasks(self) -> List[Dict]:
        """Retrieve all pending tasks"""
        tasks = self.db.collection('tasks')\
                      .where('status', '==', 'pending')\
                      .order_by('created_at')\
                      .stream()
        
        return [{**task.to_dict(), 'id': task.id} for task in tasks]
    
    def update_agent_performance(self, agent_id: str, success: bool, improvement_score: float) -> None:
        """Update agent win/loss record"""
        perf_ref = self.db.collection('agent_performance').document(agent_id)
        current = perf_ref.get()
        
        if current.exists:
            data = current.to_dict()
            data['wins'] = data.get('wins', 0) + (1 if success else 0)
            data['failures'] = data.get('failures', 0) + (0 if success else 1)
            data['total_improvement'] = data.get('total_improvement', 0) + (improvement_score if success else 0)
            data['average_improvement'] = data['total_improvement'] / data['wins'] if data['wins'] > 0 else 0
        else:
            data = {
                'wins': 1 if success else 0,
                'failures': 0 if success else 1,
                'total_improvement': improvement_score if success else 0,
                'average_improvement': improvement_score if success else 0
            }
        
        perf_ref.set(data)
        logger.info(f"Updated performance for {agent_id}: {data}")
    
    def close(self):
        """Cleanup Firebase connection"""
        firebase_admin.delete_app(firebase_admin.get_app())
        logger.info("Firebase connection closed")

# Singleton instance for global access
firebase_foundry = None

def get_firebase_instance(credential_path: Optional[str] = None):
    """Get or create Firebase instance"""
    global firebase_foundry
    if firebase_foundry is None:
        firebase_foundry = FirebaseFoundry(credential_path)
    return firebase_foundry
```

### FILE: sentinel_auditor.py
```python
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