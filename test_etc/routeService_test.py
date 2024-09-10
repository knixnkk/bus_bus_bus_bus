import requests

start_coords = ["102.820758", "16.473989"]
end_coords = ('102.714461', '16.042153')
headers = {
    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
}
call = requests.get(f'https://api.openrouteservice.org/v2/directions/driving-car?api_key=5b3ce3597851110001cf6248cfcc4ae77f384640a52cda1f7f0c71cf&start={start_coords[0]},{start_coords[1]}&end={end_coords[0]},{end_coords[1]}', headers=headers)

if call.status_code == 200:
    data = call.json()
    print(data['features'][0]['properties']['segments'][0]['distance'])
else:
    print("Request failed with status code", call.status_code)