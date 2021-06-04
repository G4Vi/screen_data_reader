#!/usr/bin/env python3
import os
import asyncio
from aiohttp import web
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import time

async def root_handler(request):
    return web.FileResponse('www/index.html')

JOBS = 0

def worker_code(data, writeend):
    import sys, io 
    time.sleep(10)   
    print(os.getpid())
    print('writeend ' + str(writeend))
    #os.write(writeend, bytes("aaaaaaaaaaaaaaaaaaa\n", "utf8"))
    oldstdout = sys.stdout
    sys.stdout =  io.TextIOWrapper(os.fdopen(writeend, "wb", 0), write_through=True)
    scriptdir = os.path.dirname(__file__)
    sys.path.insert(0, scriptdir + "/..")
    import screen_data_reader
    toret = screen_data_reader.fromBuf(data)
    os.close(writeend)
    sys.stdout = oldstdout
    return toret

PPE = ProcessPoolExecutor(max_workers=1)

async def wait_for_worker_result(worker, fd):
    print('waiting for ')
    print(worker)
    result = await worker
    os.close(fd)
    print('worker done')    

async def print_chld_stdout(read):
    pipe = os.fdopen(read, mode='r')

    loop = asyncio.get_event_loop()
    stream_reader = asyncio.StreamReader()
    def protocol_factory():
        return asyncio.StreamReaderProtocol(stream_reader)

    transport, _ = await loop.connect_read_pipe(protocol_factory, pipe)
    while True:
        text = await stream_reader.readline()
        if not text:
            break
        print('child ' + text.decode("utf-8"), end='')
    transport.close()
    print('is task done')


async def screen_data_reader_handler(request):
    if request.content_length > 104857600:
        return web.Response(status=413, text='<h1>Too much data, 100 MiB max</h1>', content_type='text/html')
    post = await request.post()

    filedata = post["file"].file.read()
    post["file"].file.close()
    #parent_conn, child_conn = mp.Pipe()
    readend, writeend = os.pipe()
    print('writeend parent ' + str(writeend))
    worker = PPE.submit(worker_code, filedata, writeend)
    worker = asyncio.wrap_future(worker)    
    asyncio.create_task(print_chld_stdout(readend))    
    asyncio.create_task(wait_for_worker_result(worker, writeend))   
    return web.Response(status=200, text='<h1>OK</h1>', content_type='text/html')
app = web.Application(client_max_size=114857600)
app.add_routes([web.get('/', root_handler), web.post('/screen_data_reader.py', screen_data_reader_handler), web.static('/', 'www')])
web.run_app(app)