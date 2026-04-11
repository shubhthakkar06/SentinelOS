import pickle
import pandas as pd

class AIAdvisor:
    def __init__(self, model_path="auv_ai_advisor.pkl"):
        self.model = None
        self.features = None
        try:
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.features = data['features']
            print("AI Advisor initialized with offine ML Model.")
        except Exception as e:
            print(f"Warning: Could not load AI model: {e}")

    def get_advisory_signal(self, task, system_state):
        if not self.model:
            return 0  # No AI adjustment
            
        # Construct single-row DataFrame matching the model features exactly
        sample = {f: 0 for f in self.features}
        
        sample['base_priority'] = task.base_priority
        sample['is_critical'] = 1 if task.critical else 0
        sample['remaining_time'] = getattr(task, "remaining_time", 0)
        sample['available_memory'] = system_state.get('available_memory', 100)
        
        task_col = f"task_type_{task.task_type}"
        if task_col in sample:
            sample[task_col] = 1
            
        df = pd.DataFrame([sample], columns=self.features)
        
        # Predict probability of fault
        try:
            fault_prob = self.model.predict_proba(df)[0][1] # Probability of class 1 (fault)
        except Exception:
            return 0
            
        # Advisory Logic: Boost priority directly proportional to risk
        if fault_prob > 0.5:
            return 10  # Urgent priority boost
        elif fault_prob > 0.3:
            return 5   # Moderate priority boost
            
        return 0
