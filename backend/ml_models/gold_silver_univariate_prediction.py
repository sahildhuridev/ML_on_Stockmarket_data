import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from sklearn.linear_model import LinearRegression
import numpy as np

def analyze_gold_silver_univariate(interval='1y'):
    """
    Fetches, predicts, and returns Gold & Silver data for the given interval using Univariate models.
    """
    print(f"Fetching data from Yahoo Finance for GLD and SLV (Univariate)... (Interval: {interval})")
    data = yf.download(["GLD", "SLV"], period="max")
    
    if 'Adj Close' in data.columns:
        prices = data['Adj Close']
    else:
        prices = data['Close']
    
    prices = prices.dropna()
    
    # Determine resampling and prediction length based on interval
    if interval == '1y':
        resampled_prices = prices.resample('YE').last()
        prediction_steps = 10
        freq_str = 'YE'
    elif interval == '3mo':
        resampled_prices = prices.resample('QE').last()
        prediction_steps = 8 # 2 years
        freq_str = 'QE'
    elif interval == '1mo':
        resampled_prices = prices.resample('ME').last()
        prediction_steps = 12 # 1 year
        freq_str = 'ME'
    elif interval == '1d':
        resampled_prices = prices # Daily data, no resample
        prediction_steps = 30 # 1 month
        freq_str = 'D'
    else:
        return {"error": "Invalid interval."}
    
    df = resampled_prices.copy()
    if len(df) < 2:
        return {"error": "Not enough data to resample and train!"}

    df.reset_index(inplace=True)
    df['TimeIndex'] = range(len(df))
    
    # 4. Fit Linear Regression models (Univariate: TimeIndex only)
    X = df[['TimeIndex']].values
    y_gld = df['GLD'].values
    y_slv = df['SLV'].values
    
    lr_gld = LinearRegression()
    lr_gld.fit(X, y_gld)
    
    lr_slv = LinearRegression()
    lr_slv.fit(X, y_slv)
    
    # 5. Predict for next steps
    last_time = df['TimeIndex'].max()
    future_time_indices = np.array([[last_time + i] for i in range(1, prediction_steps + 1)])
    
    pred_gld = lr_gld.predict(future_time_indices)
    pred_slv = lr_slv.predict(future_time_indices)
    
    # Create DataFrames for predictions
    last_date = df['Date'].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=prediction_steps, freq=freq_str)
    
    predictions_df = pd.DataFrame({
        'Date': future_dates,
        'TimeIndex': future_time_indices.flatten(),
        'Predicted_GLD': pred_gld,
        'Predicted_SLV': pred_slv
    })
    
    # Explainability
    import shap
    import lime
    import lime.lime_tabular

    explainer_shap_gld = shap.LinearExplainer(lr_gld, X)
    shap_values_gld = explainer_shap_gld.shap_values(X)
    
    explainer_shap_slv = shap.LinearExplainer(lr_slv, X)
    shap_values_slv = explainer_shap_slv.shap_values(X)
    
    gld_shap_importance = np.abs(shap_values_gld).mean(axis=0).tolist()
    slv_shap_importance = np.abs(shap_values_slv).mean(axis=0).tolist()
    
    shap_data = {
        "features": ["TimeIndex"],
        "gld_importance": gld_shap_importance,
        "slv_importance": slv_shap_importance
    }
    
    lime_explainer_gld = lime.lime_tabular.LimeTabularExplainer(
        X, feature_names=["TimeIndex"], class_names=['GLD_Price'], mode='regression'
    )
    exp_gld = lime_explainer_gld.explain_instance(X[-1], lr_gld.predict, num_features=1)
    lime_gld_dict = exp_gld.as_list()
    
    lime_explainer_slv = lime.lime_tabular.LimeTabularExplainer(
        X, feature_names=["TimeIndex"], class_names=['SLV_Price'], mode='regression'
    )
    exp_slv = lime_explainer_slv.explain_instance(X[-1], lr_slv.predict, num_features=1)
    lime_slv_dict = exp_slv.as_list()
    
    lime_data = {
        "explained_instance_year": int(X[-1][0]),
        "gld_explanation": lime_gld_dict,
        "slv_explanation": lime_slv_dict
    }

    # Format JSON payload
    historical_data = []
    display_history_limit = 100 if interval == '1d' else 200
    df_recent = df.tail(display_history_limit)
    
    for index, row in df_recent.iterrows():
        date_str = str(row['Date'].date())
        historical_data.append({
            "Date": date_str,
            "Year": date_str if interval != '1y' else int(row['Date'].year),
            "Actual_GLD": round(row['GLD'], 2),
            "Actual_SLV": round(row['SLV'], 2)
        })
        
    prediction_data = []
    for index, row in predictions_df.iterrows():
        date_str = str(row['Date'].date())
        prediction_data.append({
            "Date": date_str,
            "Year": date_str if interval != '1y' else int(row['Date'].year),
            "Predicted_GLD": round(row['Predicted_GLD'], 2),
            "Predicted_SLV": round(row['Predicted_SLV'], 2)
        })
        
    return {
        "historical": historical_data,
        "predictions": prediction_data,
        "explanations": {
            "shap": shap_data,
            "lime": lime_data
        }
    }
