import requests
import json

url = "http://localhost:5000/predict"
data = {
    "LB": 100, 
    "LT": 120, 
    "KT": 3, 
    "KM": 2, 
    "GRS": 1
}

try:
    response = requests.post(url, json=data)
    print("Status Code:", response.status_code)
    try:
        print("Response:", json.dumps(response.json(), indent=2))
    except:
        print("Raw Response:", response.text)
except Exception as e:
    print("Error:", e)
