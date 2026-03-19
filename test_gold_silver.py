import os
import sys

# Add the backend directory to sys.path
backend_dir = r"c:\Users\Sahil\Desktop\bizmetric\bizmetric_sahil_fsd\ML_Stock_analysis\backend"
sys.path.append(backend_dir)

# Mock Django settings if needed, but gold_silver_prediction doesn't seem to use them directly
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from ml_models.gold_silver_prediction import analyze_gold_silver_multivariate

def test_analysis():
    print("Starting test...")
    try:
        result = analyze_gold_silver_multivariate(interval='1y')
        if "error" in result:
            print(f"Error in result: {result['error']}")
        else:
            print("Success!")
            print(f"Historical data points: {len(result['historical'])}")
            print(f"Prediction data points: {len(result['predictions'])}")
            print(f"SHAP data keys: {result['explanations']['shap'].keys()}")
            print(f"LIME data keys: {result['explanations']['lime'].keys()}")
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analysis()
