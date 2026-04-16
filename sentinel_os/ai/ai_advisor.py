import pickle
import pandas as pd
import os
from pathlib import Path

class AdvisoryRecommendation:
    """Structured recommendation from AI Advisor with reasoning"""
    def __init__(self, task_id, action, confidence, reasoning):
        self.task_id = task_id
        self.action = action  # "BOOST_PRIORITY", "MONITOR", "SCHEDULE_EARLY", "DEFER"
        self.confidence = confidence  # 0.0 to 1.0
        self.reasoning = reasoning
        self.fault_probability = None
        self.risk_factors = []
        
    def __str__(self):
        return f"[{self.action}] Task {self.task_id} | Confidence: {self.confidence:.1%} | {self.reasoning}"

class AIAdvisor:
    def __init__(self, model_path=None):
        self.model = None
        self.features = None
        self.last_recommendation = None
        self.last_confidence = 0
        self.advisor_interventions = 0
        
        # Try multiple paths to find the model
        if model_path is None:
            paths_to_try = [
                "auv_ai_advisor.pkl",
                "sentinel_os/ai/auv_ai_advisor.pkl",
                str(Path(__file__).parent / "auv_ai_advisor.pkl"),
                "/Users/shubhthakkar/Projects/SentinelOS/sentinel_os/ai/auv_ai_advisor.pkl",
            ]
        else:
            paths_to_try = [model_path]
            
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        data = pickle.load(f)
                        self.model = data['model']
                        self.features = data['features']
                    print(f"✅ AI Advisor initialized with offline ML Model from: {path}")
                    return
                except Exception as e:
                    print(f"⚠️  Failed to load model from {path}: {e}")
                    continue
                    
        print("⚠️  Warning: Could not load AI model from any path. AI features disabled.")

    def analyze_task_risk(self, task, system_state):
        """Analyze task for fault risk - returns (fault_prob, risk_factors)"""
        if not self.model:
            return 0.0, []
            
        risk_factors = []
        
        try:
            # Construct feature vector
            sample = {f: 0 for f in self.features}
            
            sample['base_priority'] = task.base_priority
            sample['is_critical'] = 1 if task.critical else 0
            sample['remaining_time'] = getattr(task, "remaining_time", 0)
            sample['available_memory'] = system_state.get('available_memory', 100)
            
            # Analyze risk factors
            if sample['is_critical']:
                risk_factors.append("Critical task - higher priority, more failure-prone")
            if sample['available_memory'] < 20:
                risk_factors.append("Memory pressure detected")
            if task.deadline and sample['remaining_time'] > 0:
                time_ratio = sample['remaining_time'] / max(1, task.deadline)
                if time_ratio < 0.3:
                    risk_factors.append("Approaching deadline urgently")
            
            # Set task type encoding
            task_col = f"task_type_{task.task_type}"
            if task_col in sample:
                sample[task_col] = 1
                
            df = pd.DataFrame([sample], columns=self.features)
            
            # Get fault probability
            fault_prob = self.model.predict_proba(df)[0][1]
            return fault_prob, risk_factors
            
        except Exception as e:
            print(f"  ⚠️  AI Analysis error: {e}")
            return 0.0, []

    def get_advisory_signal(self, task, system_state):
        """
        IMPROVED: Returns advisory boost with reasoning
        Returns: boost_value (int) for priority adjustment
        """
        if not self.model:
            return 0
            
        fault_prob, risk_factors = self.analyze_task_risk(task, system_state)
        
        # Store for logging
        self.last_confidence = fault_prob
        
        # Smart Advisory Logic: Graduated response based on risk
        # Only intervene when there's strong evidence
        if fault_prob > 0.8:
            boost = 12
            action = "URGENT_BOOST"
            reason = f"Critical fault risk ({fault_prob:.1%})"
        elif fault_prob > 0.65:
            boost = 8
            action = "STRONG_BOOST"
            reason = f"High fault risk ({fault_prob:.1%})"
        elif fault_prob > 0.5:
            boost = 4
            action = "MODERATE_BOOST"
            reason = f"Moderate fault risk ({fault_prob:.1%})"
        elif fault_prob > 0.3:
            boost = 1
            action = "LIGHT_BOOST"
            reason = f"Mild fault risk ({fault_prob:.1%})"
        else:
            boost = 0
            action = "MONITOR"
            reason = f"Low fault risk ({fault_prob:.1%})"
        
        # Create recommendation object
        self.last_recommendation = AdvisoryRecommendation(
            task.tid, action, fault_prob, reason
        )
        self.last_recommendation.fault_probability = fault_prob
        self.last_recommendation.risk_factors = risk_factors
        
        if boost > 0:
            self.advisor_interventions += 1
            
        return boost

    def get_last_recommendation(self):
        """Get detailed reasoning from last advisory"""
        return self.last_recommendation
    
    def get_advisor_stats(self):
        """Return AI advisor statistics"""
        return {
            "interventions": self.advisor_interventions,
            "last_confidence": self.last_confidence,
            "model_loaded": self.model is not None
        }
