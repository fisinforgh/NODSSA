import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from scipy.stats import shapiro
import os
from diagnosticos import correr_tests
# 1) Cargar los datos con lags
df = pd.read_parquet("../data/processed/ozone_2005_2025_lags.parquet").dropna()

# 2) Definir X (lags 1–12) e y
lags = [f"Ozone_lag{lag}" for lag in range(1,13)]
X = df[lags]
X = sm.add_constant(X)
y = df["Ozone"]

# 3) Ajustar modelo OLS
model = sm.OLS(y, X).fit()

# 4) Imprimir resumen
print(model.summary())

# 5) Diagnósticos de supuestos
print("\n--- Pruebas de supuestos ---")
# Normalidad
stat_sw, p_sw = shapiro(model.resid)
print(f"Shapiro–Wilk p-valor = {p_sw:.3f}")
# Homocedasticidad
bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, model.model.exog)
print(f"Breusch–Pagan p-valor = {bp_p:.3f}")
# Independencia (Ljung-Box en lag 10)
lb = acorr_ljungbox(model.resid, lags=[10], return_df=True)
print(lb)
# Durbin-Watson
dw = sm.stats.stattools.durbin_watson(model.resid)
print(f"Durbin–Watson = {dw:.3f}")

# 6) Guardar residuos y predicciones
df_out = df.assign(fitted=model.fittedvalues, resid=model.resid)
os.makedirs("../data/processed", exist_ok=True)
df_out.to_parquet("../data/processed/ols_results.parquet")
print("\n💾 Resultados OLS guardados en data/processed/ols_results.parquet")
# 7) Diagnósticos
df_res = correr_tests(
    y=model.resid,              # residuos
    exog=df[lags]               # exógenas (lags usadas)
)
os.makedirs("../data/processed", exist_ok=True)
df_res.to_csv("../data/processed/diagnostics_OLS.csv", index=False)
print("💾 Diagnósticos OLS guardados en data/processed/diagnostics_OLS.csv")
