import requests

url = "http://127.0.0.1:8000/api/v1/documents/upload"
headers = {
    "Authorization": "Bearer <YOUR_TOKEN>" # I will replace this or just see what it returns
}

# we'll just test if it connects and returns 401 Unauthorized
try:
    response = requests.post(url)
    print(f"Status: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
