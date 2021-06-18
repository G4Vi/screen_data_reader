# Server setup

Instructions based on using Ubuntu 20.04 focal minimal on 0rac1e compute free tier [*shhh*]

## Install server dependencies
`sudo apt-get install git python3 python3-pip python3-venv nginx vim`

## Setup Screen Data Reader with python
`git clone https://github.com/G4Vi/screen_data_reader.git`

`cd screen_data_reader`

### Create venv

`python3 -m venv .venv`

Activate venv `$ source .venv/bin/activate`

Update pip `(.venv)$ pip install --upgrade pip`

`pip install opencv-python aiohttp`

## Network setup

Modify VCN security list to allow TCP 80 and 443 (done on $CLOUD_HOST) or port forward your router.

Allow through OS firewall
```
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT
```

Verify the rules `sudo iptables -L INPUT -v -n`

## Nginx / TLS setup

Follow https://certbot.eff.org/lets-encrypt/ubuntufocal-nginx

Edit `/etc/nginx/sites-available/default` and modify the server block used for SSL (with the certbot keys)
```
client_max_body_size 125M;
location / {
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-NginX-Proxy true;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_pass http://localhost:8080/;
        proxy_ssl_session_reuse off;
        proxy_set_header Host $http_host;
        proxy_pass_header Server;
        proxy_cache_bypass $http_upgrade;
        proxy_redirect off;
        proxy_buffering off;
    }
``` 

## Install and launch the service 
```   
sudo cp server/screen_data_reader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable screen_data_reader.service
sudo systemctl start screen_data_reader.service
```