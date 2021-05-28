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

## Run

outside env: `$ ./screen_data_reader.sh`

from venv: `(.venv)$ ./screen_data_reader.py`

See `--help` . By default the filename provided by psx_screen_dumper is used and saved to current directory.

## License
MIT, see `LICENSE`
