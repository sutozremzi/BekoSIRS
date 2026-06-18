import requests
import json

url = 'http://127.0.0.1:8000/api/v1/stock-intelligence/dashboard/'
print(f"Testing {url} ...")
try:
    response = requests.get(url, timeout=30)
    print("Status Code:", response.status_code)
    try:
        print("Response:", json.dumps(response.json(), indent=2))
    except:
        print("Text Response:", response.text)
except Exception as e:
    print("Error:", e)
