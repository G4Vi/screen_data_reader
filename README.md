screen_data_reader
==================

Read data from the psx's screen via video or screen recording

Used for locating and decoding images outputted by [psx_screen_dumper](https://github.com/G4Vi/psx_screen_dumper). 

The psx appears to be too slow to generate QR codes in realtime, so this was created.

## Install

`git clone` and `cd ` repo.

Create venv `$ python3 -m venv .venv`

Activate venv `$ source .venv/bin/activate`

Update pip `(.venv)$ pip install --upgrade pip`

Install requirements `(.venv)$ pip install -r requirements.txt`

### For capturing from Windows desktop in addition to reading from video

Also `pip install mss pywin32`

### For capturing from X11 desktop in addition to reading from video

Also `pip install mss xlib`

## Run

outside env: `$ ./screen_data_reader.sh`

from venv: `(.venv)$ ./screen_data_reader.py`

See `--help` . By default the filename provided by psx_screen_dumper is used and saved to current directory.

## License
MIT, see `LICENSE`

## Running web app instance

`pip install aiohttp`, run `server/server.py` and navigate to `http://127.0.0.1:8080`

See `server/README.md` for nginx reverse proxy setup

## Running basic web app instance
Run `basic_server/server.py` and navigate to `http://127.0.0.1:8080`