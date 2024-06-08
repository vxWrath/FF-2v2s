import aiohttp
import datetime

from typing import Optional, Dict, Any, List

class RobloxUser:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        
        self.banned = kwargs.get('isBanned', False)
        self.name   = kwargs.get('name')
        self.display_name = kwargs.get('displayName')
        self.description  = kwargs.get('description', '')
        
        created = kwargs.get('created', None)
        
        if created is not None:
            self.created = datetime.datetime.fromisoformat(created)
        else:
            self.created = None
            
    def __repr__(self):
        return f"<User name={self.name!r} display_name={self.display_name!r}"
    
    def __str__(self):
        return self.display_name or self.name
    
    @property
    def profile_url(self):
        return f"https://www.roblox.com/users/{self.id}/profile"
    
class RobloxClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def request(self, method: str, subdomain: str, path: str = "", params: Optional[Dict[str, Any]]=None, request_json: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
        async with self.session.request(method, f"https://{subdomain}.roblox.com/{path}", params=params, json=request_json) as response:
            return await response.json()
        
    async def get_users(self, user_ids: List[int]) -> List[RobloxUser]:
        response = await self.request("post", "users", f"v1/users", request_json={"userIds": user_ids, "excludeBannedUsers": True})
        
        if response.get('data') is None or len(response['data']) == 0:
            return []
        return [RobloxUser(**x) for x in response['data']]

    async def get_user(self, user_id: int) -> Optional[RobloxUser]:
        response = await self.request("get", "users", f"v1/users/{user_id}")
        
        if response.get('errors') is None:
            return RobloxUser(**response)

    async def get_user_by_name(self, username: str) -> Optional[RobloxUser]:
        response = await self.request("post", "users", f"v1/usernames/users", request_json={"usernames": [username], "excludeBannedUsers": True})
        
        if response.get('data') is None or len(response['data']) == 0:
            return
        return RobloxUser(**response['data'][0])
    
    async def get_users_avatar(self, user_ids: List[int], size: Optional[str]="352x352"):
        data = await self.request("get", "thumbnails", f"v1/users/avatar-headshot", params={
            "userIds": ','.join([str(x) for x in user_ids]),
            "size": size,
            "format": "Png",
            "isCircular": "false"
        })
        
        return {x['targetId']: x['imageUrl'] for x in data['data']}
    
    async def verify_private_server(self, url: str):
        pass