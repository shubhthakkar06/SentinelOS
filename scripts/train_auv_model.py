# %% [markdown]
# # AUV Fault Prediction & Resource Prioritization Model Training
# This notebook/script will read the 5000 simulation frames we just generated, train an offline 
# lightweight machine learning model (RandomForest), and save it so we can hook it into SentinelOS.
# Since an AUV has no internet connection, this model is extremely small and runs purely locally.

# %%
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

# %% [markdown]
# ## 1. Load the Generated Dataset
# We load the dataset generated from the SentinelOS simulation.

# %%
df = pd.read_csv('data/auv_task_data.csv')
print(f"Loaded {len(df)} samples.")
df.head()

# %% [markdown]
# ## 2. Feature Engineering
# The AI needs to know the task type. We will convert the categorical `task_type` text into numerical values.

# %%
# One-hot encode task types
df_encoded = pd.get_dummies(df, columns=['task_type'])

# Features we are feeding into the model
X = df_encoded.drop(columns=['system_time', 'task_id', 'fault_occurred'])

# Target: Did a fault occur? (DEADLINE_MISS or RESOURCE_FAILURE)
y = df_encoded['fault_occurred']

# Split into 80% training data, 20% testing data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print("Features used:", list(X.columns))

# %% [markdown]
# ## 3. Train the Offline Model
# We're using a Random Forest Classifier because it evaluates extremely fast on embedded hardware, 
# making it perfect for an offline AUV.

# %%
clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
clf.fit(X_train, y_train)

# %% [markdown]
# ## 4. Evaluate the Model
# Let's see how well it learned to predict faults based on system memory and task priorities.

# %%
y_pred = clf.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# %% [markdown]
# ## 5. Export Model and Feature Columns
# We need to save BOTH the trained model and the exact feature columns it expects so the SentinelOS AI hook knows how to format its inputs.

# %%
model_data = {
    'model': clf,
    'features': list(X.columns)
}

with open('auv_ai_advisor.pkl', 'wb') as f:
    pickle.dump(model_data, f)

print("✅ Model successfully saved to 'auv_ai_advisor.pkl'")
print("SentinelOS can now load this file for offline AI advisory!")

# %%
