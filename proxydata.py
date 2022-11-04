import json

class ProxyRequest:
    def __init__(self, http_method: str, endpoint: str, body: str, uuid: str, http_headers: dict[str:str]=None):
        self.http_method = http_method
        self.http_headers = http_headers
        self.endpoint = endpoint
        self.body = body
        self.uuid = uuid
    
    def from_json(json_str: str):
        return ProxyRequest(**json.loads(json_str))

class ProxyResponse:
    def __init__(self, uuid: str, http_code: int, body: str=None, error: str=None):
        self.uuid = uuid
        self.http_code = http_code
        self.body = body
        self.error = error
    
    def from_error(uuid: str, error: str):
        return ProxyResponse(uuid, 500, error=error)
    
    def to_json(self) -> str:
        return json.dumps(self.__dict__)