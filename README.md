screen_data_reader
==================

Read data from a screenshot or picture of screen

Used for parsing custom data format outputted by a psx app as the psx is too slow at generating QR codes.

See [psx_screen_dumper](https://github.com/G4Vi/psx_screen_dumper)

# Install

`git clone` and `cd ` repo.

Create venv `$ python3 -m venv .env`

Activate venv `$ source .venv/bin/activate`

Update pip `(.venv)$ pip install --upgrade pip`

Install requirements `(.venv)$ pip install -r requirements.txt`

# Run

outside env: `$ ./readdata.sh`

from venv: `(.venv)$ ./readdata.py`


