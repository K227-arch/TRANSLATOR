import requests, json
from pathlib import Path

PROJECT_ID = 'prj_G0zF62MYIMaySJcsPADaAt4lddrI'
TEAM_ID    = 'team_K6qRP6TF3XwvLK3IqAp7cZYl'

# Check ~/.vercel/auth.json for the Vercel token
vercel_token = ''
vercel_config = Path.home() / '.vercel' / 'auth.json'
if vercel_config.exists():
    data = json.loads(vercel_config.read_text())
    vercel_token = data.get('token', '')
    print('Found Vercel auth token in ~/.vercel/auth.json')
else:
    print('No ~/.vercel/auth.json found')

if not vercel_token:
    print('No Vercel token available — cannot fetch env vars via API')
else:
    r = requests.get(
        f'https://api.vercel.com/v9/projects/{PROJECT_ID}/env',
        headers={'Authorization': f'Bearer {vercel_token}'},
        params={'teamId': TEAM_ID},
        timeout=15
    )
    print(f'Vercel API status: {r.status_code}')
    if r.status_code == 200:
        envs = r.json().get('envs', [])
        print(f'Total env vars: {len(envs)}')
        for e in envs:
            key = e.get('key', '')
            etype = e.get('type', '')
            eid = e.get('id', '')[:8]
            print(f'  {key} [{etype}] id={eid}')
    else:
        print(r.text[:300])
