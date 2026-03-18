import httpx 
 
async def fetch_emails(access_token: str, params: dict) -> dict: 
    count = params.get('count', 5) 
    async with httpx.AsyncClient() as client: 
        resp = await client.get( 
            'https://gmail.googleapis.com/gmail/v1/users/me/messages', 
            headers={'Authorization': f'Bearer {access_token}'}, 
            params={'maxResults': count} 
        ) 
    if resp.status_code != 200: 
        return {'error': resp.text} 
 
    messages = resp.json().get('messages', []) 
    # Fetch snippet for each message 
    results = [] 
    async with httpx.AsyncClient() as client: 
        for msg in messages: 
            detail = await client.get( 
                
f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg["id"]}', 
                headers={'Authorization': f'Bearer {access_token}'}, 
                params={'format': 'metadata', 'metadataHeaders': ['Subject', 
'From']} 
            ) 
            results.append(detail.json()) 
    return {'emails': results}


async def create_calendar_event(access_token: str, params: dict) -> dict: 
    event_body = { 
        'summary': params.get('title', 'New Event'), 
        'start': {'dateTime': params.get('start'), 'timeZone': 'UTC'}, 
        'end':   {'dateTime': params.get('end'),   'timeZone': 'UTC'}, 
    } 
    async with httpx.AsyncClient() as client: 
        resp = await client.post( 
            'https://www.googleapis.com/calendar/v3/calendars/primary/events', 
            headers={'Authorization': f'Bearer {access_token}'}, 
            json=event_body 
        ) 
    return resp.json() 

async def create_github_issue(access_token: str, params: dict) -> dict: 
    owner = params.get('owner')   # GitHub username 
    repo  = params.get('repo')    # repo name 
    async with httpx.AsyncClient() as client: 
        resp = await client.post( 
            f'https://api.github.com/repos/{owner}/{repo}/issues', 
            headers={ 
                'Authorization': f'Bearer {access_token}', 
                'Accept': 'application/vnd.github+json' 
            }, 
            json={ 
                'title': params.get('title', 'New Issue'), 
                'body':  params.get('body', '') 
            } 
        ) 
    return resp.json() 