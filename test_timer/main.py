import requests

# Define the URL and payload
url = 'http://192.168.2.14:5000/timer'
payload = {'seconds': 10}  # Example payload with 10 seconds countdown

# Send the POST request with JSON data
response = requests.post(url, json=payload)

# Print the response from the server
print(response.json())
