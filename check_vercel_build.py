import urllib.request, json, os

authpath = os.path.expandvars('%APPDATA%/com.vercel.cli/Data/auth.json')
with open(authpath) as f:
    token = json.load(f)['token']

url = 'https://api.vercel.com/v6/deployments?projectId=prj_G0zF62MYIMaySJcsPADaAt4lddrI&teamId=team_K6qRP6TF3XwvLK3IqAp7cZYl&limit=1&target=production'
req = urllib.request.Request(url)
req.add_header('Authorization', 'Bearer ' + token)
with urllib.request.urlopen(req) as r:
    data = json.load(r)
    dep = data['deployments'][0]
    dep_id = dep['uid']
    print('ID:', dep_id, '| State:', dep['readyState'])

url2 = 'https://api.vercel.com/v3/deployments/' + dep_id + '/events?follow=0&limit=100'
req2 = urllib.request.Request(url2)
req2.add_header('Authorization', 'Bearer ' + token)
with urllib.request.urlopen(req2) as r:
    events = json.load(r)
    errors = [e['text'] for e in events if e.get('type') == 'stderr' and e.get('text','').strip()]
    print("=== STDERR LINES ===")
    for e in errors[-20:]:
        print(e)
