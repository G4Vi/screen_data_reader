#!/usr/bin/env python3
import sys, os
import asyncio
import aiohttp
from aiohttp import web
from aiohttp.web_exceptions import HTTPFound, HTTPTemporaryRedirect
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import secrets
import struct
import pickle
from enum import Enum

class WorkerMsg(Enum):
    OUT    = 1
    RESULT = 2

class ClientMsg(Enum):
    OUT    = 1
    RESULT = 2

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class StdoutMpPipe:

    def windowssend(self, obj):
        pickled = pickle.dumps(obj)
        n = len(pickled)
        if n > 0x7FFFFFFF:
            header = struct.pack("!i", -1)
            header = header + struct.pack("!Q", n)
        else:
            header = struct.pack("!i", n)
        self.writeend.send_bytes(header+pickled)

    def unixsend(self, obj):
        self.writeend.send(obj)

    def __init__(self, writeend):
        self.writeend = writeend
        self.jobid = '-1'
        platform = sys.platform
        # we send length header on windows too because of using StreamReader reading instead of multiprocessing.recv
        if platform == "win32":                              
            self.send = self.windowssend
        else:       
            self.send = self.unixsend

    def write(self,msg):
        #self.writeend.send({ 'jobid' : self.jobid, 'msgid' : WorkerMsg.OUT, 'data' : msg})
        self.send({ 'jobid' : self.jobid, 'msgid' : WorkerMsg.OUT, 'data' : msg})
        
        
    def flush(self):
        sys.__stdout__.flush()

def worket_init(queueargs):
    import sys, io
    print('spawning worker ' + str(os.getpid()))
    
    # set stdout to the pipe 
    writeend = queueargs.get()
    sys.stdout = StdoutMpPipe(writeend)

    # import the library
    scriptdir = os.path.dirname(__file__)
    sys.path.insert(0, scriptdir + "/..")
    global screen_data_reader
    import screen_data_reader
    
def worker_code(data, jobid):
    sys.stdout.jobid = jobid   
    print('running job on ' + str(os.getpid()))
    try:
        toret = screen_data_reader.fromBuf(data)
    except Exception as e:
        print(e.args[0])
        print("Job failed, make sure your video is focused with good lighting and the data patterns have the correct aspect ratio!")
        toret = None
    # ignore messages until the next job
    sys.stdout.jobid = '-1'
    # send the response on the pipe to ensure it comes after the other messages
    sys.stdout.send({ 'jobid' : jobid, 'msgid' : WorkerMsg.RESULT, 'data' : toret})    

async def StreamReader_recv_bytes(self, maxsize=None):
    # read the size
    buf = await self.readexactly(4)
    size, = struct.unpack("!i", buf)
    if size == -1:
        buf = self.readexactly(8)
        size, = struct.unpack("!Q", buf)
    if maxsize is not None and size > maxsize:
        return None
    # read the message
    return await self.readexactly(size)

async def StreamReader_recv(self):
    buf = await StreamReader_recv_bytes(self)
    return pickle.loads(buf)
    

async def handle_worker_messages(read):    
    pipe = read
    loop = asyncio.get_event_loop()
    stream_reader = asyncio.StreamReader()
    def protocol_factory():
        return asyncio.StreamReaderProtocol(stream_reader)

    transport, _ = await loop.connect_read_pipe(protocol_factory, pipe)
    while True:
        msg = await StreamReader_recv(stream_reader)
        if not msg['jobid'] in JOBS:
            print('Unknown jobid')
            continue
        job = JOBS[msg['jobid']]
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
                endtext = '</pre>'
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
        else:
            print('unhandled message')

             
    transport.close()
    print('is task done')

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
async def screen_data_reader_handler(request):
    if request.content_length > 104857600:
        return web.Response(status=413, text='<h1>Too much data, 100 MiB max</h1>', content_type='text/html')
    post = await request.post()

    filedata = post["file"].file.read()
    post["file"].file.close()
    tok = secrets.token_urlsafe()
    JOBS[tok] = { 'clients' : [], 'message' : '<html><head><title>' + TMPLWWW['BASETITLE'] + ': ' + tok + '</title></head>' + bodyfirst('..') +'<h3>Job Output</h3><pre>', 'qp' : -1}
    JOBS[tok]['message'] =  JOBS[tok]['message'] + 'new job: ' + tok + "\n"   
    PPE.submit(worker_code, filedata, tok)
    JOBS[tok]['qp'] = len(PPE._pending_work_items)-1
    JOBS[tok]['message'] =  JOBS[tok]['message'] + 'queue position: ' + str(JOBS[tok]['qp']) + "\n"   
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

async def dumpworkitems():
    while True:
        print('qc ' + str(PPE._queue_count))
        print('num work items ' + str(len(PPE._pending_work_items)))
        await asyncio.sleep(1)

async def main():
    global TMPLWWW
    TMPLWWW = {'BASETITLE' : 'Screen Data Reader'}
    scriptdir = os.path.dirname(__file__)
    for entry in os.scandir(scriptdir + '/tmpl-www'):
        print('tmplwww: ' + entry.path + ' name: ' + entry.name)
        with open(entry.path, 'r') as file:
            TMPLWWW[entry.name] = file.read()
        
    
    global JOBS
    JOBS = {}
    MAXWORKERS = 1
    
    # create the worker pool    
    writeendQueue = mp.Queue()
    for wi in range(0, MAXWORKERS):
        worker = mp.Pipe(duplex=False)
        # for race condtion starting pipe?
        await asyncio.sleep(1)
        asyncio.create_task(handle_worker_messages(worker[0]))
        writeendQueue.put(worker[1])
    global PPE
    PPE = ProcessPoolExecutor(max_workers=MAXWORKERS, initializer=worket_init, initargs=(writeendQueue,))
    #asyncio.create_task(dumpworkitems())    
        
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
