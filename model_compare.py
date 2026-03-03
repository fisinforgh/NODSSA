import pandas as pd
import numpy as np
import os
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from diagnosticos import correr_tests

# Cargar datos con lags
df = pd.read_parquet("../data/processed/ozone_2005_2025_lags.parquet").dropna()

# Definir train/test split (80% train, 20% test)
split_idx = int(len(df) * 0.8)
df_train = df.iloc[:split_idx]
df_test = df.iloc[split_idx:]

# Variables predictoras: lags 1–12
lags = [f"Ozone_lag{lag}" for lag in range(1, 13)]
X_train = df_train[lags].values
y_train = df_train["Ozone"].values
X_test = df_test[lags].values
y_test = df_test["Ozone"].values

# Función de métricas
def compute_metrics(y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if np.all(y_true != 0) else np.nan
    r2 = r2_score(y_true, y_pred)
    return rmse, mae, mape, r2

# Grids de alpha
grids = {
    'Ridge': [0.1, 1, 10, 100],
    'Lasso': [0.001, 0.01, 0.1, 1]
}

results = []
diagnostics = []

# Entrenar y evaluar cada modelo en la grid
for model_name, alphas in grids.items():
    for alpha in alphas:
        # Selección del modelo
        if model_name == 'Ridge':
            model = Ridge(alpha=alpha)
        else:
            model = Lasso(alpha=alpha, max_iter=10000)
        # Entrenamiento\        
        model.fit(X_train, y_train)
        # Predicciones\        
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)
        # Cálculo de métricas\        
        train_rmse, train_mae, train_mape, train_r2 = compute_metrics(y_train, y_train_pred)
        test_rmse, test_mae, test_mape, test_r2 = compute_metrics(y_test, y_test_pred)
        # Almacenar resultados\        
        results.append({
            'model': model_name,
            'alpha': alpha,
            'dataset': 'train',
            'RMSE': train_rmse,
            'MAE': train_mae,
            'MAPE': train_mape,
            'R2': train_r2
        })
        results.append({
            'model': model_name,
            'alpha': alpha,
            'dataset': 'test',
            'RMSE': test_rmse,
            'MAE': test_mae,
            'MAPE': test_mape,
            'R2': test_r2
        })
        # Diagnósticos sobre residuos del test set
        resid = y_test - y_test_pred
        exog_df = pd.DataFrame({'fitted': y_test_pred}, index=df_test.index)
        df_diag = correr_tests(pd.Series(resid, index=df_test.index), exog=exog_df)
        df_diag.insert(0, 'model', model_name)
        df_diag.insert(1, 'alpha', alpha)
        diagnostics.append(df_diag)

# Guardar resultados de métricas en CSV
os.makedirs("../data/processed", exist_ok=True)
results_df = pd.DataFrame(results)
results_df.to_csv("../data/processed/compare_regularization.csv", index=False)
print("💾 Resultados de regularización guardados en data/processed/compare_regularization.csv")

# Guardar diagnósticos en CSV
if diagnostics:
    diag_df = pd.concat(diagnostics, ignore_index=True)
    diag_df.to_csv("../data/processed/diagnostics_regularization.csv", index=False)
    print("💾 Diagnósticos de regularización guardados en data/processed/diagnostics_regularization.csv")
else:
    print("⚠️  No se generaron diagnósticos para regularización.")

