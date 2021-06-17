sudo apt-get install git python3 python3-pip python3-venv vim

git clone https://github.com/G4Vi/screen_data_reader.git

Create venv

pip install opencv-python aiohttp
Modify VCN security list to allow TCP 8080, 80, and 443


sudo iptables -I INPUT 1 -p tcp --dport 8080 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT

sudo iptables -L INPUT -v -n
sudo apt-get install nginx
https://certbot.eff.org/lets-encrypt/ubuntufocal-nginx
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
    }
sudo cp server/screen_data_reader.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable screen_data_reader.service
sudo systemctl start screen_data_reader.service