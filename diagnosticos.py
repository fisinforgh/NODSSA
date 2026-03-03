# python/diagnosticos.py

import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from scipy.stats import shapiro

def correr_tests(y: pd.Series, exog: pd.DataFrame = None, alpha: float = 0.05) -> pd.DataFrame:
    """
    Ejecuta una batería de tests sobre los residuos de un modelo OLS:
    - Shapiro–Wilk (normalidad)
    - Breusch–Pagan (homocedasticidad)
    - Durbin–Watson (autocorrelación)
    - Ljung–Box (autocorrelación múltiple, lag=10)
    Devuelve un DataFrame con Test, Statistic, p-value y Reject H0?.
    """
    # Si no se pasan exógenas, usamos solo intercepto
    if exog is None:
        exog = pd.DataFrame({"const": 1}, index=y.index)
    model = sm.OLS(y, sm.add_constant(exog, has_constant='add')).fit()
    resid = model.resid

    # 1) Shapiro–Wilk
    sw_stat, sw_p = shapiro(resid)

    # 2) Breusch–Pagan
    bp_stat, bp_p, _, _ = het_breuschpagan(resid, model.model.exog)

    # 3) Durbin–Watson
    dw_stat = sm.stats.stattools.durbin_watson(resid)

    # 4) Ljung–Box (lag=10)
    lb = acorr_ljungbox(resid, lags=[10], return_df=True).iloc[0]
    lb_stat, lb_p = lb["lb_stat"], lb["lb_pvalue"]

    tests = [
        ("Shapiro–Wilk", sw_stat, sw_p, sw_p < alpha),
        ("Breusch–Pagan", bp_stat, bp_p, bp_p < alpha),
        ("Durbin–Watson", dw_stat, None, (dw_stat < 1.5) or (dw_stat > 2.5)),
        ("Ljung–Box χ²", lb_stat, lb_p, lb_p < alpha),
    ]

    df = pd.DataFrame([{
        "Test": t,
        "Statistic": stat,
        "p-value": p,
        "Reject H0?": rej
    } for t, stat, p, rej in tests])

    return df

