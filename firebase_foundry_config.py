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