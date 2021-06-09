#!/usr/bin/env python3
import os
import asyncio
import aiohttp
from aiohttp import web
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import time
import secrets
from aiohttp.helpers import content_disposition_header

from aiohttp.web_exceptions import HTTPFound, HTTPTemporaryRedirect
import sys
MAXWORKERS = 1

async def root_handler(request):
    return web.FileResponse('www/index.html')

class StdoutMpPipe:
    def __init__(self, writeend):
        self.writeend = writeend

    def write(self,msg):
        #self.writeend.send(msg)
        msg = bytes(msg, 'utf-8')
        self.writeend.send_bytes(msg)

    def flush(self):
        sys.__stdout__.flush()

def worket_init(queueargs):
    import sys, io
    print('spawning worker ' + str(os.getpid()))
    # set stdout to the pipe 
    writeend = queueargs.get()
    sys.stdout = StdoutMpPipe(writeend)
    #sys.stdout =  io.TextIOWrapper(os.fdopen(writeend, "wb", 0), write_through=True)
    #sys.stdout =  writeend
    # import the library
    scriptdir = os.path.dirname(__file__)
    sys.path.insert(0, scriptdir + "/..")
    global screen_data_reader
    import screen_data_reader
    

def worker_code(data, jobid):   
    print('new job ' + str(jobid) + ' on ' + str(os.getpid()))    
    toret = screen_data_reader.fromBuf(data)
    return toret

async def client_cleanup(client, endtext):
    await client["response"].write(bytes(endtext, 'utf-8'))
    client["toalert"].set()

async def wait_for_worker_result(worker, jobid):
    print('waiting for ')
    print(worker)
    result = await worker
    print('worker done')

    # job is done, setup the results
    endtext = '</pre> <a href="file?id=' + jobid + '">' + result[0] + '</a><iframe id="invisibledownload" style="display:none;" src="file?id=' + jobid + '"></iframe>'
    JOBS[jobid]["message"] = JOBS[jobid]["message"] + endtext
    JOBS[jobid]["file"] = result
    JOBS[jobid]["done"] = True
    
    
    # job is done, no more active clients
    clients = JOBS[jobid]["clients"]
    JOBS[jobid]["clients"] = []

    # notify existing clients about the results
    await asyncio.gather(*[ client_cleanup(client, endtext) for client in clients]) 
   
   
    
    

async def print_chld_stdout(read):
    #pipe = os.fdopen(read, mode='r')
    pipe = read
    loop = asyncio.get_event_loop()
    stream_reader = asyncio.StreamReader()
    def protocol_factory():
        return asyncio.StreamReaderProtocol(stream_reader)

    transport, _ = await loop.connect_read_pipe(protocol_factory, pipe)
    while True:
        text = await stream_reader.readline()
        if not text:
            break
        strtext = text.decode("utf-8")
        print('child ' + strtext, end='')
        for key in JOBS.keys():
            JOBS[key]["message"] = JOBS[key]["message"] + strtext
            for client in JOBS[key]["clients"]:
                await client["response"].write(text)            
    transport.close()
    print('is task done')


WORKERPOOL = []
for wi in range(0, MAXWORKERS):
    #WORKERPOOL.append(os.pipe())
    WORKERPOOL.append(mp.Pipe(duplex=False))
writeendQueue = mp.Queue()
[writeendQueue.put(i[1]) for i in WORKERPOOL]
PPE = ProcessPoolExecutor(max_workers=MAXWORKERS, initializer=worket_init, initargs=(writeendQueue,))
JOBS = {}

async def screen_data_reader_handler(request):
    if request.content_length > 104857600:
        return web.Response(status=413, text='<h1>Too much data, 100 MiB max</h1>', content_type='text/html')
    post = await request.post()

    filedata = post["file"].file.read()
    post["file"].file.close()
    tok = secrets.token_urlsafe()
    worker = PPE.submit(worker_code, filedata, tok)
    JOBS[tok] = { 'clients' : [], 'message' : '<pre>'}
    worker = asyncio.wrap_future(worker)    
    asyncio.create_task(wait_for_worker_result(worker, tok))  
    jobpath = "job?id=" + tok
    raise HTTPFound(location=jobpath)

async def client_follow(job, response):
    doneEvent = asyncio.Event()
    if not "done" in job:
        job["clients"].append({'response' : response, 'toalert': doneEvent})
    else:
        doneEvent.set()
    await response.write(job["message"].encode('utf-8'))
    return await doneEvent.wait()

async def job_status_page(request):
    job = JOBS[request.query['id']]
    if not job:
        return web.Response(status=404, text='No job found')    
    response = web.StreamResponse(headers={'Content-Type': 'text/html'})
    await response.prepare(request)
    await client_follow(job, response)   
    await response.write_eof()
    return response

async def file_requested(request):
    job = JOBS[request.query['id']]
    if not job or not 'file' in job:
        return web.Response(status=404, text='No job found') 
    cd = 'attachment; filename="' + job["file"][0] + '"'  
    response = web.Response(body=job['file'][1],  headers={'Content-Disposition' : cd})
    return response

app = web.Application(client_max_size=114857600)
app.add_routes([web.get('/', root_handler), web.post('/screen_data_reader.py', screen_data_reader_handler), web.get('/job', job_status_page), web.get('/file', file_requested), web.static('/', 'www')])
#web.run_app(app)
async def main():
    for worker in WORKERPOOL:
        asyncio.create_task(print_chld_stdout(worker[0]))     
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())