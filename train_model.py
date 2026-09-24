import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

# 1. Load dataset
data = pd.read_csv("dataset/accounts.csv")

# 2. Features
X = data.drop("label", axis=1)

# 3. Target
y = data["label"]

# 4. Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 5. Create model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

# 6. Train model
model.fit(X_train, y_train)

# 7. Test model
y_pred = model.predict(X_test)

# 8. Accuracy
accuracy = accuracy_score(y_test, y_pred)

print("Model trained successfully!")
print("Accuracy:", accuracy)

# 9. Classification report
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 10. Create model folder
os.makedirs("model", exist_ok=True)

# 11. Save trained model
joblib.dump(model, "model/fake_account_model.pkl")

print("\nModel saved successfully!")
print("Location: model/fake_account_model.pkl")