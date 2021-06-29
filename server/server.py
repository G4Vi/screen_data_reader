#!/usr/bin/env python3
import sys, os
import asyncio
import aiohttp
from aiohttp import web
from aiohttp.web_exceptions import HTTPFound, HTTPTemporaryRedirect
import secrets
import struct
import pickle
from enum import Enum
from collections import deque

class WorkerMsg(Enum):
    OUT    = 1
    RESULT = 2

class ClientMsg(Enum):
    OUT    = 1
    RESULT = 2

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# inspired by multiprocessing.connection.Connection
async def StreamReader_recv_bytes(self, maxsize=None):
    # read the size
    try:
        buf = await self.readexactly(4)
    except:
        print('failed read size')
        raise
    size, = struct.unpack("!i", buf)
    if size == -1:
        buf = await self.readexactly(8)
        size, = struct.unpack("!Q", buf)
    if maxsize is not None and size > maxsize:
        return None
    # read the message
    try:
        return await self.readexactly(size)
    except:
        print('failed read message')
        raise

# inspired by multiprocessing.connection.Connection
async def StreamReader_recv(self):
    buf = await StreamReader_recv_bytes(self)
    return pickle.loads(buf)
    

async def handle_job_messages(job, stream_reader):
    while True:
        try:
            msg = await StreamReader_recv(stream_reader)
        except:
            print('TASK FAILED')
            msg = {'msgid' : WorkerMsg.RESULT, 'data' : None}       
        if msg['msgid'] == WorkerMsg.OUT:
            if 'qp' in job:
                job.pop('qp')            
            job['message'] = job['message'] + msg['data']
            print(msg['data'], end='')
            data = bytes(msg['data'], 'utf-8')
            for client in job["clients"]:
                # shouldn't actually block ever
                await client_write(client, ClientMsg.OUT, data)                
        elif msg['msgid'] == WorkerMsg.RESULT:
            if msg['data'] is not None:
                job["file"] = msg['data']
                endtext = '</pre> <a href="file">' + msg['data'][0] + '</a><iframe id="invisibledownload" style="display:none;" src="file"></iframe>'
            else:           
                endtext = "JOB FAILED\n</pre>"
            endtext += TMPLWWW['footer.html']
            job["message"] = job["message"] + endtext
            job["done"] = True

            # update queue positions
            for jid in JOBS:
                # if there's no queue position job is running or has run
                jb = JOBS[jid]
                if not 'qp' in jb:
                    continue
                jb['qp'] = jb['qp'] - 1
                qpmsg = 'queue position: ' + str(jb['qp']) + "\n"
                jb['message'] = jb['message'] + qpmsg
                for client in jb["clients"]:
                    # shouldn't actually block ever
                    await client_write(client, ClientMsg.OUT, bytes(qpmsg, 'utf-8'))  

            # job is done, no more active clients
            clients = job["clients"]
            job["clients"] = []
            # notify existing clients about the results
            data = bytes(endtext, 'utf-8')
            for client in clients:
                asyncio.create_task(client_write(client, ClientMsg.RESULT, data))
            break             
        else:
            print('unhandled message')             
    print('job ' + job['id'] + ' task done')

async def client_write(client, id, data):
    await client['msgqueue'].put({'msgid' : id, 'data' : data})

async def client_follow(job, response):
    jobdone = "done" in job
    msgqueue = asyncio.Queue()    
    if not jobdone:
        job["clients"].append({'msgqueue' : msgqueue})    
    await response.write(job["message"].encode('utf-8'))
    if jobdone:
        return
    # output the job's messages
    while True:
        msg = await msgqueue.get()
        await response.write(msg['data'])
        if msg['msgid'] == ClientMsg.RESULT:
            break

def bodyfirst(rootpath):
    bf = TMPLWWW['body-first.html']
    bf = bf.replace('$ROOTPATH', rootpath)
    return bf

async def run_job(job):
    global NUM_CURRENT_WORKERS
    NUM_CURRENT_WORKERS = NUM_CURRENT_WORKERS + 1
    print("running job " + job['id'])
    scriptdir = os.path.dirname(__file__)

    proc = await asyncio.create_subprocess_exec(sys.executable, scriptdir+'/worker.py', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)

    asyncio.create_task(handle_job_messages(job, proc.stdout))
    proc.stdin.write(job['filedata'])
    del job['filedata']
    await proc.stdin.drain()    
    proc.stdin.close()
    await proc.stdin.wait_closed()

    await proc.wait()
    NUM_CURRENT_WORKERS = NUM_CURRENT_WORKERS-1    
    print('proc done')
    if len(WORKERQUEUE) > 0:
        job = WORKERQUEUE.popleft()
        asyncio.create_task(run_job(job))

    

async def screen_data_reader_handler(request):
    if request.content_length > 104857600:
        return web.Response(status=413, text='<h1>Too much data, 100 MiB max</h1>', content_type='text/html')
    post = await request.post()

    # read in the input data
    filedata = post["file"].file.read()
    post["file"].file.close()
    
    # send some padding data so the response is streamed (Firefox needs this)
    paddata = 'a'*1024
    padstr = '<div style="display:none;">' + paddata + '</div>'

    # create the job
    tok = secrets.token_urlsafe()
    JOBS[tok] = { 'clients' : [], 'message' : '<html><head><title>' + TMPLWWW['BASETITLE'] + ': ' + tok + '</title></head>' + bodyfirst('..') +'<h3>Job Output</h3>' + padstr + '<pre>', 'qp' : -1, 'id': tok}
    JOBS[tok]['filedata'] = filedata
    JOBS[tok]['message'] =  JOBS[tok]['message'] + 'new job: ' + tok + "\n"
    JOBS[tok]['qp'] = len(WORKERQUEUE)
    if NUM_CURRENT_WORKERS == MAXWORKERS:
        JOBS[tok]['qp'] = JOBS[tok]['qp'] + 1
    JOBS[tok]['message'] =  JOBS[tok]['message'] + 'queue position: ' + str(JOBS[tok]['qp']) + "\n" 
 
    # the job queue is empty when not all workers are in use so just run the job
    if NUM_CURRENT_WORKERS < MAXWORKERS:        
        asyncio.create_task(run_job(JOBS[tok]))
    else:
    # otherwise enqueue the job
        print("not running job yet " + tok)
        WORKERQUEUE.append(JOBS[tok])

    # redirect to the job status page
    jobpath = tok + "/job"
    raise HTTPFound(location=jobpath)

async def job_status_page(request):
    jobid = request.match_info['jobid'] 
    if not jobid in JOBS:
        return web.Response(status=404, text='No job found')
    job = JOBS[jobid]   
    response = web.StreamResponse(headers={'Content-Type': 'text/html'})
    await response.prepare(request)
    await client_follow(job, response)   
    await response.write_eof()
    return response

async def file_requested(request):
    jobid = request.match_info['jobid'] 
    if not jobid in JOBS:
        return web.Response(status=404, text='No job found')
    job = JOBS[jobid]        
    cd = 'attachment; filename="' + job["file"][0] + '"'  
    response = web.Response(body=job['file'][1],  headers={'Content-Disposition' : cd})
    return response

async def root_handler(request):
    return web.Response(text='<html><head><title>' + TMPLWWW['BASETITLE'] + '</title></head>' + bodyfirst('.') + TMPLWWW['index.html'] + TMPLWWW['footer.html'], content_type='text/html')

async def main():
    print('pid ' + str(os.getpid()))
    # load in templates
    global TMPLWWW
    TMPLWWW = {'BASETITLE' : 'Screen Data Reader'}
    scriptdir = os.path.dirname(__file__)
    for entry in os.scandir(scriptdir + '/tmpl-www'):
        print('tmplwww: ' + entry.path + ' name: ' + entry.name)
        with open(entry.path, 'r') as file:
            TMPLWWW[entry.name] = file.read()        
    
    # setup JOB queue
    global JOBS
    JOBS = {}
    global MAXWORKERS
    MAXWORKERS = 1
    global NUM_CURRENT_WORKERS
    NUM_CURRENT_WORKERS = 0
    global WORKERQUEUE
    WORKERQUEUE = deque()
        
    # launch the web server
    app = web.Application(client_max_size=114857600)
    app.add_routes([web.get('/', root_handler), web.get('/index.htm', root_handler), web.get('/index.html', root_handler), web.post('/screen_data_reader.py', screen_data_reader_handler), web.get('/{jobid}/job', job_status_page), web.get('/{jobid}/file', file_requested), web.static('/', scriptdir+'/www')])     
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
