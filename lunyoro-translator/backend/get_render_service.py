import urllib.request
import json

key = "rnd_knvi3m9VzshhNcwXPk7NrdAQytVC"
headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
service_id = "srv-d7t202vavr4c73fek8v0"

req = urllib.request.Request(
    "https://api.render.com/v1/services/" + service_id,
    headers=headers
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())

print(json.dumps(data, indent=2))
