import json
import requests
url = 'http://localhost:8065/api/v4/users';
payload = {
}
headers = {
    'Authorization': 'Bearer ' + '7kspqpcps3fpxeo8u6h7bdazxw',
    'Accept': 'application/json'
}
response = requests.get(url, data=json.dumps(payload), headers=headers)
other = 'foo'