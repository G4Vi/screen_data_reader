#!/usr/bin/env python3
from aiohttp import web

async def root_handler(request):
    return web.FileResponse('www/index.html')

JOBS = 0

async def screen_data_reader_handler(request):
    if request.content_length > 104857600:
        return web.Response(status=413, text='<h1>Too much data, 100 MiB max</h1>', content_type='text/html')
    post = await request.post()

    filedata = post["file"].file.read()  

    
    return web.Response(status=200, text='<h1>OK</h1>', content_type='text/html')
app = web.Application(client_max_size=114857600)
app.add_routes([web.get('/', root_handler), web.post('/screen_data_reader.py', screen_data_reader_handler), web.static('/', 'www')])
web.run_app(app)