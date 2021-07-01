screen_data_reader
==================

Read data from the psx(Sony PlayStation)'s screen via video or screen recording

Used for locating and decoding images outputted by [psx_screen_dumper](https://github.com/G4Vi/psx_screen_dumper). 

`screen_data_reader` parses a custom format for the data patterns as the psx appears to be too slow to generate QR codes in realtime (at least with off-the-shelf libraries)

Feel free to try it via [Web App](https://psx-sdr.computoid.com/)

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

## Run CLI

outside env: `$ ./screen_data_reader.sh`

from venv: `(.venv)$ ./screen_data_reader.py`

See `--help` . By default the filename provided by psx_screen_dumper is used and saved to current directory.

## Running web app instance

`pip install aiohttp`, run `server/server.py` and navigate to `http://127.0.0.1:8080`

See `server/README.md` for nginx reverse proxy setup

## License
MIT, see `LICENSE`

## Help

Feel free to ask in the [PSXDEV discord](https://discord.gg/QByKPpH) 

## Running basic web app instance
Run `basic_server/server.py` and navigate to `http://127.0.0.1:8080`