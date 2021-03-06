#!/usr/bin/env python3
import sys, os, getopt
import asyncio
import aiohttp
from aiohttp import web
from aiohttp.web_exceptions import HTTPFound, HTTPTemporaryRedirect
import secrets
import struct
import pickle
from enum import Enum
from collections import deque

# communication with worker
from jobmsg import JobMsg

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# inspired by multiprocessing.connection.Connection
class StreamReaderConnection:

    def __init__(self, stream_reader):
        self.sr = stream_reader

    async def recv_bytes(self, maxsize=None):
        # read the size
        try:
            buf = await self.sr.readexactly(4)
        except:
            print('failed read size')
            raise
        size, = struct.unpack("!i", buf)
        if size == -1:
            buf = await self.sr.readexactly(8)
            size, = struct.unpack("!Q", buf)
        if maxsize is not None and size > maxsize:
            return None
        # read the message
        try:
            return await self.sr.readexactly(size)
        except:
            print('failed read message')
            raise
    
    async def recv(self):
        buf = await self.recv_bytes()
        return pickle.loads(buf)

class ClientMsg(Enum):
    OUT    = 1
    RESULT = 2

async def client_write(client, id, data):
    await client['msgqueue'].put({'msgid' : id, 'data' : data})

async def client_follow(job, response):
    jobdone = hasattr(job, 'done')
    msgqueue = asyncio.Queue()    
    if not jobdone:
        job.clients.append({'msgqueue' : msgqueue})    
    await response.write(job.html.encode('utf-8'))
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

class Job:
    def __init__(self, filedata):
        self.id = secrets.token_urlsafe()
        self.filedata = filedata
        self.clients = []        
        
        # build the html
        # firefox needs padding data to stream the response
        paddata = 'a'*1024
        padstr = '<div style="display:none;">' + paddata + '</div>'
        self.html = '<html><head><title>' + TMPLWWW['BASETITLE'] + ': ' + self.id + '</title></head>' + bodyfirst('..') +'<h3>Job Output</h3>' + padstr + '<pre>'
        self.html = self.html + 'new job: ' + self.id + "\n"        
        
    def _appendhtml(self, toadd):
        self.html = self.html + toadd

    async def add_to_page(self, msg, isEnd=False):
        self._appendhtml(msg)
        if not isEnd:
            msgtype = ClientMsg.OUT
        else:
            self.done = True
            msgtype = ClientMsg.RESULT

        data = bytes(msg, 'utf-8')
        clients = self.clients
        # job is done, no more active clients
        if isEnd:
            del self.clients
        # msg the current clients with the data too
        for client in clients:
            # shouldn't actually block ever
            await client_write(client, msgtype, data)   

    async def process_messages(self, stream_reader):
        srconn = StreamReaderConnection(stream_reader)
        while True:
            try:
                msg = await srconn.recv()
            except:
                print('TASK FAILED')
                msg = {'msgid' : JobMsg.RESULT, 'data' : None}       
            if msg['msgid'] == JobMsg.OUT:
                print(msg['data'], end='')
                await self.add_to_page(msg['data'])             
            elif msg['msgid'] == JobMsg.RESULT:
                if msg['data'] is not None:
                    self.file = msg['data']
                    endtext = '</pre> <a href="file">' + msg['data'][0] + '</a><iframe id="invisibledownload" style="display:none;" src="file"></iframe>'
                else:           
                    endtext = "JOB FAILED\n</pre>"
                endtext += TMPLWWW['footer.html']
                await self.add_to_page(endtext, True)                
                break             
            else:
                print('unhandled message')             
        print('job ' + self.id + ' process_messages done')
    
    async def run(self):
        scriptdir = os.path.dirname(__file__)
        proc = await asyncio.create_subprocess_exec(sys.executable, scriptdir+'/worker.py', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
    
        asyncio.create_task(self.process_messages(proc.stdout))
        proc.stdin.write(self.filedata)
        del self.filedata
        await proc.stdin.drain()    
        proc.stdin.close()
        await proc.stdin.wait_closed()
    
        return await proc.wait()

class JobManager:
    def __init__(self, maxworkers):
        self.MAXWORKERS = maxworkers
        self.jobs = {}
        self.num_current_workers = 0
        self.jobqueue = asyncio.Queue()

        # launch queue workers
        for i in range(maxworkers):
            asyncio.create_task(self.task_run_jobs())


    def create_job(self, filedata):
        # create the job
        job = Job(filedata)
        qp = self.jobqueue.qsize()
        if self.num_current_workers == self.MAXWORKERS:
            qp = qp+1
        job._appendhtml( 'queue position: ' + str(qp) + "\n")
        self.jobs[job.id] = job

        # enqueue the job
        self.jobqueue.put_nowait(job)

        return job

    def get_job(self, jid):
        return self.jobs[jid]

    async def task_run_jobs(self):
        while True:
            # get a job and note worker is use
            job = await self.jobqueue.get()
            self.num_current_workers  = self.num_current_workers  + 1        
            # actually run the job
            print("running job " + job.id)
            try:
                await job.run()
            except:
                pass
            # update queue positions
            qp = 0
            for jb in self.jobqueue._queue:
                qpmsg = 'queue position: ' + str(qp) + "\n"
                try:
                    # shouldn't actually block ever
                    await jb.add_to_page(qpmsg)
                except:
                    pass            
                qp = qp + 1
            # note job is done, worker is free
            self.jobqueue.task_done()  
            self.num_current_workers  = self.num_current_workers -1    
            print('finished job ' + job.id)
        
    

async def screen_data_reader_handler(request):
    if request.content_length > 104857600:
        return web.Response(status=413, text='<h1>Too much data, 100 MiB max</h1>', content_type='text/html')
    post = await request.post()

    # read in the input data
    filedata = post["file"].file.read()
    post["file"].file.close()    

    # create the job
    job = JM.create_job(filedata)    

    # redirect to the job status page
    jobpath = job.id + "/job"
    raise HTTPFound(location=jobpath)

async def job_status_page(request):
    jobid = request.match_info['jobid']
    try:
        job = JM.get_job(jobid)
    except:
        return web.Response(status=404, text='No job found')        
  
    response = web.StreamResponse(headers={'Content-Type': 'text/html'})
    await response.prepare(request)
    await client_follow(job, response)   
    await response.write_eof()
    return response

async def file_requested(request):
    jobid = request.match_info['jobid'] 
    try:
        job = JM.get_job(jobid)
    except:
        return web.Response(status=404, text='No job found')           
    cd = 'attachment; filename="' + job.file[0] + '"'  
    response = web.Response(body=job.file[1],  headers={'Content-Disposition' : cd})
    return response

async def root_handler(request):
    return web.Response(text='<html><head><title>' + TMPLWWW['BASETITLE'] + '</title></head>' + bodyfirst('.') + TMPLWWW['index.html'] + TMPLWWW['footer.html'], content_type='text/html')

async def main():
    print('pid ' + str(os.getpid()))
    
    # parse arguments
    argv = sys.argv[1:]
    def usage(code):
        print('screen_data_reader.py [-j num_workers]')
        sys.exit(code)
    MAXWORKERS = 1
    try:
        opts, args = getopt.getopt(argv,"hj:",["help", "jobs="])
    except getopt.GetoptError:        
        usage(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-j", "--jobs"):
            MAXWORKERS = int(arg)

    # load in templates
    global TMPLWWW
    TMPLWWW = {'BASETITLE' : 'Screen Data Reader'}
    scriptdir = os.path.dirname(__file__)
    for entry in os.scandir(scriptdir + '/tmpl-www'):
        print('tmplwww: ' + entry.path + ' name: ' + entry.name)
        with open(entry.path, 'r') as file:
            TMPLWWW[entry.name] = file.read()        
    
    # setup the JobManager    
    global JM
    JM = JobManager(MAXWORKERS)
        
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
