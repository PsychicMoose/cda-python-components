#!/usr/bin/env python3

import asyncio
import logging
import aiocoap.resource as resource
import aiocoap

logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG

class SensorResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.content = b'{"temperature": 22.5, "humidity": 45}'

    async def render_get(self, request):
        print("=" * 50)
        print("GET REQUEST RECEIVED IN SENSOR RESOURCE!")
        print(f"Request code: {request.code}")
        print(f"Request payload: {request.payload}")
        print("=" * 50)
        return aiocoap.Message(payload=self.content)

async def main():
    root = resource.Site()
    root.add_resource(['sensor'], SensorResource())
    
    context = await aiocoap.Context.create_server_context(root, bind=('127.0.0.1', 5683))
    
    print("CoAP Server started on coap://127.0.0.1:5683")
    print("Test with: coap://127.0.0.1:5683/sensor")
    
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())