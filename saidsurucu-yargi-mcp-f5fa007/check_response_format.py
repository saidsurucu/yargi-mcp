#!/usr/bin/env python3
from fastmcp import Client
from mcp_server_main import app
import json
import asyncio

async def check_response_format():
    client = Client(app)
    async with client:
        result = await client.call_tool('search_bedesten_unified', {
            'phrase': 'mülkiyet',
            'court_types': ['YARGITAYKARARI'],
            'birimAdi': 'H1',
            'pageSize': 3
        })
        if result and result.content:
            data = json.loads(result.content[0].text)
            print('Response keys:', list(data.keys()))
            print('Sample response:', json.dumps(data, indent=2, ensure_ascii=False)[:500])

asyncio.run(check_response_format())