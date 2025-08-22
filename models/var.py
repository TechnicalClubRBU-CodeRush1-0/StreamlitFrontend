import numpy as np
import pandas as pd

class VaRCalculator:
    def __init__(self, returns: pd.Series):
        if not isinstance(returns, pd.Series):
            raise TypeError("returns must be a pandas Series")
        self.returns = returns.dropna()

    def calculate_var(self, confidence_level=0.95):
        alpha = 1 - confidence_level
        var_value = np.percentile(self.returns, alpha * 100)
        return -var_value

    def calculate_cvar(self, confidence_level=0.95):
        var_value = self.calculate_var(confidence_level)
        tail = self.returns[self.returns <= -var_value]
        if tail.empty:
            return 0.0
        return -tail.mean()