import glob
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from extract import cargar_ozono

# 1) Listar y cargar todos los archivos HE5 de 2005
files = sorted(glob.glob("../data/raw_test/aura_2005/*.he5"))
dfs = [cargar_ozono(f) for f in files]
df = pd.concat(dfs).sort_values("Date").reset_index(drop=True)

# 2) Preparar X e y para regresión: tiempo secular vs ozono
X = np.arange(len(df)).reshape(-1,1)  # 0,1,2,...
y = df["Ozone"].values

# 3) Ajustar modelo y mostrar R²
model = LinearRegression().fit(X, y)
print(f"R² simple (2005): {model.score(X, y):.3f}")
