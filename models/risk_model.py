import math

class StockInvestmentModel:
    DEFAULT_WEIGHTS = {
        'de_ratio': 0.25,
        'beta': 0.25,
        'earnings_volatility': 0.20,
        'sector_risk': 0.15,
        'macro_risk': 0.15
    }
    DEFAULT_CONFIDENCE_WEIGHTS = {
        'sentiment_confidence': 0.40,
        'risk_data_confidence': 0.60
    }

    def __init__(self, weights=None, confidence_weights=None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.confidence_weights = confidence_weights or self.DEFAULT_CONFIDENCE_WEIGHTS

    @staticmethod
    def normalize_de_ratio(v):
        if v is None or (isinstance(v,float) and math.isnan(v)): return 0.5
        if v > 2: return 1.0
        if v >= 1: return 0.5
        return 0.0

    @staticmethod
    def normalize_beta(v):
        if v is None or (isinstance(v,float) and math.isnan(v)): return 0.5
        if v > 1.5: return 1.0
        if v >= 1.0: return 0.5
        return 0.0

    @staticmethod
    def normalize_earnings_vol(v):
        if v is None or (isinstance(v,float) and math.isnan(v)): return 0.5
        if v > 0.30: return 1.0
        if v > 0.15: return 0.5
        return 0.0

    @staticmethod
    def normalize_sector_risk(v):
        if not v: return 0.5
        return {'high':1.0,'medium':0.5,'low':0.0}.get(v.lower(),0.5)

    @staticmethod
    def normalize_macro_risk(v):
        if v is None or (isinstance(v,float) and math.isnan(v)): return 0.5
        return min(max(v,0.0),1.0)

    def calculate_risk_score(self, de_ratio, beta, earnings_volatility, sector_risk, macro_risk):
        return (
            self.normalize_de_ratio(de_ratio) * self.weights['de_ratio'] +
            self.normalize_beta(beta) * self.weights['beta'] +
            self.normalize_earnings_vol(earnings_volatility) * self.weights['earnings_volatility'] +
            self.normalize_sector_risk(sector_risk) * self.weights['sector_risk'] +
            self.normalize_macro_risk(macro_risk) * self.weights['macro_risk']
        )

    @staticmethod
    def risk_level(score):
        if score < 0.33: return "Low"
        if score < 0.66: return "Medium"
        return "High"

    def investment_assessment(self, sentiment_score, risk_score):
        risk_lvl = self.risk_level(risk_score)
        if sentiment_score > 0.3:
            if risk_lvl == 'Low': return 'Low Risk Investment', 'High', 'Buy'
            if risk_lvl == 'Medium': return 'Medium Risk Investment', 'Medium', 'Hold'
            return 'Medium to High Risk Investment', 'Medium', 'Hold'
        if -0.3 <= sentiment_score <= 0.3:
            if risk_lvl == 'Low': return 'Medium Risk Investment', 'Medium', 'Hold'
            if risk_lvl == 'Medium': return 'Medium Risk Investment', 'Medium', 'Hold'
            return 'High Risk Investment', 'High', 'Sell'
        if risk_lvl == 'Low': return 'Medium to High Risk Investment', 'Medium', 'Hold/Sell (cautious)'
        if risk_lvl == 'Medium': return 'High Risk Investment', 'High', 'Sell'
        return 'Very High Risk Investment', 'Very High', 'Sell'

    def calculate_confidence(self, sentiment_confidence, risk_data_confidence):
        cw = self.confidence_weights
        score = (sentiment_confidence or 0) * cw['sentiment_confidence'] + \
                (risk_data_confidence or 0) * cw['risk_data_confidence']
        return score * 100.0

    def full_assessment(self, *, sentiment_score, de_ratio, beta,
                        earnings_volatility, sector_risk, macro_risk,
                        sentiment_confidence, risk_data_confidence):
        risk_score = self.calculate_risk_score(de_ratio, beta, earnings_volatility, sector_risk, macro_risk)
        assessment, _, action = self.investment_assessment(sentiment_score, risk_score)
        confidence_percent = self.calculate_confidence(sentiment_confidence, risk_data_confidence)
        return {
            'sentiment_score': sentiment_score,
            'risk_score': risk_score,
            'risk_level': self.risk_level(risk_score),
            'assessment': assessment,
            'confidence_percent': confidence_percent,
            'recommended_action': action,
            'de_ratio': de_ratio,
            'beta': beta,
            'earnings_volatility': earnings_volatility
        }