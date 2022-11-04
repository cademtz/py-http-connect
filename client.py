from threading import Thread
from proxydata import ProxyRequest, ProxyResponse
from aiohttp.typedefs import URL, LooseHeaders
import traceback
import aiohttp
import asyncio
import socket
import struct
import queue

class Client:
    def __init__(self, dst_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dst_port = dst_port
        self.asyncio_loop = asyncio.new_event_loop()
        self.session = aiohttp.ClientSession(loop=self.asyncio_loop)

        self.write_thread = Thread(target=self.write_loop, daemon=True)
        self.asyncio_thread = Thread(target=lambda: self.asyncio_loop.run_forever(), daemon=True)
        self.write_queue = queue.Queue()
    
    def connect(self, *args, **kwargs) -> None:
        self.sock.connect(*args, **kwargs)

    def read_loop(self):
        while True:
            json_str = self._recv().decode('utf-8')
            req = ProxyRequest.from_json(json_str)
            print(f'method: {req.http_method}, endpoint: {req.endpoint}, uuid: {req.uuid}, body: {req.body}')
            asyncio.run_coroutine_threadsafe(self._handle_request(req), self.asyncio_loop)
    
    def write_loop(self):
        try:
            while True:
                resp: ProxyResponse = self.write_queue.get(block=True)
                self._send(resp.to_json())
        except Exception as e:
            print(f'Exception: {e}')
            print(traceback.format_exc())
    
    async def _handle_request(self, req: ProxyRequest):
        try:
            #url = URL.build(host=f'127.0.0.1', port=self.dst_port, path=req.endpoint)
            url = f'http://127.0.0.1:{self.dst_port}{req.endpoint}'
            async with self.session.request(method=req.http_method, url=url, headers=req.http_headers, data=req.body) as resp_:
                resp: aiohttp.ClientResponse = resp_
                print(resp)
                
                proxy_resp = ProxyResponse(req.uuid, resp.status)
                proxy_resp.body = (await resp.read()).decode('utf-8')
                if resp.status < 200 or resp.status >= 300:
                    proxy_resp.error = str(resp.status)
                self.write_queue.put(proxy_resp, block=True)

        except Exception as e:
            print(f'Exception {e}')
            print(traceback.format_exc())
            self._send(ProxyResponse.from_error(req.uuid, str(e)).to_json())
    
    def __enter__(self):
        self.sock.__enter__()
        self.write_thread.start()
        self.asyncio_thread.start()
        return self
    
    def __exit__(self, *args, **kwargs):
        self.sock.__exit__(*args, **kwargs)
        self.write_thread.join(timeout=0)
        self.asyncio_thread.join(timeout=0)

    def _send(self, buf: bytes|str):
        if type(buf) == str:
            buf = buf.encode('utf-8')
        
        total_sent = 0
        while total_sent < len(buf):
            sent = self.sock.send(buf[total_sent:])
            if sent == 0:
                raise RuntimeError('Socket writing is closed')
            total_sent += sent

    def _recv(self):
        len_buffer = b''
        while len(len_buffer) < 4:
            chunk = self.sock.recv(4 - len(len_buffer))
            if len(chunk) == 0:
                raise RuntimeError('Socket reading is closed')
            len_buffer += chunk

        msg_len = struct.unpack("!I", len_buffer)[0]
        if msg_len <= 0:
            raise RuntimeError('Message length is invalid')

        total_read = 0
        chunks = []
        while total_read < msg_len:
            chunk = self.sock.recv(msg_len - total_read)
            if len(chunk) == 0:
                raise RuntimeError('Socket reading is closed')
            chunks.append(chunk)
            total_read += len(chunk)

        return b''.join(chunks)