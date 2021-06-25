import sys, os
import struct
import pickle
from enum import Enum
scriptdir = os.path.dirname(__file__)
sys.path.insert(0, scriptdir + "/..")
import screen_data_reader

class WorkerMsg(Enum):
    OUT    = 1
    RESULT = 2



class PickleStdout():
    def __init__(self):
        self.old_stdout=sys.stdout

    def send(self, obj):
        pickled = pickle.dumps(obj)
        n = len(pickled)
        if n > 0x7FFFFFFF:
            header = struct.pack("!i", -1)
            header = header + struct.pack("!Q", n)
        else:
            header = struct.pack("!i", n)
        self.old_stdout.buffer.write(header+pickled)

    def write(self, msg):
        self.send({ 'jobid' : 'filler', 'msgid' : WorkerMsg.OUT, 'data' : msg})
    
    def flush(self):
        self.old_stdout.flush()


if __name__ == "__main__":
    sys.stdout = PickleStdout()

    print('running job on ' + str(os.getpid()))
    inputdata = sys.stdin.buffer.read()
    toret = screen_data_reader.fromBuf(inputdata)

    # send the response on the pipe to ensure it comes after the other messages
    sys.stdout.send({ 'jobid' : 'filler', 'msgid' : WorkerMsg.RESULT, 'data' : toret})    
    
    
    