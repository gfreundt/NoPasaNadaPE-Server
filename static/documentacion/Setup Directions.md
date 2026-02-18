# 🚀 Deploy Flask App with Gunicorn + NGINX on Google Cloud VM

## ✅ System Info

- **External IP:** `34.194.43.253`  
- **Internal IP:** `10.128.0.4`  
- **Flask App Path:** `/home/nopasanadape/NoPasaNadaPE/server`  
- **App Entry File:** `main.py`  
- **Flask App Object Name:** `app`  
- **Gunicorn Location:** `/home/nopasanadape/NoPasaNadaPE/server/.venv/bin/gunicorn`

---

## 1. 🔧 Update System and Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install nginx lsof curl nano -y
```

## 2. Change Time Zone

```bash
sudo timedatectl set-timezone America/Lima 
```

## 3. Load GIT code

```bash
sudo apt-get install git
git clone https://github.com/gfreundt/NoPasaNadaPE.git
```

Username for 'https://github.com': gfreundt <br>
Password for 'https://gfreundt@github.com': 


## 4. ✅ Make Sure Python Environment Is Set Up

When using `uv`:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
cd /home/nopasanadape/NoPasaNadaPE/server

uv venv .venv
source .venv/bin/activate
uv pip install flask gunicorn
```

## 5. 🔥 Test Flask App With Gunicorn

From your app directory:

```bash
cd /home/nopasanadape/NoPasaNadaPE/server
.venv/bin/gunicorn --bind 10.128.0.4:5000 main:app
```

---

## 4. ⚙️ Configure NGINX as Reverse Proxy

Create a config file:

```bash
sudo nano /etc/nginx/sites-available/nopasanadape
```

Paste this:

```nginx
server {
    listen 80;
    server_name 34.194.43.253;
    client_max_body_size 20M;

    location / {
        proxy_pass http://10.128.0.4:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/nopasanadape /etc/nginx/sites-enabled/
```

Check NGINX config:

```bash
sudo nginx -t
```

Restart NGINX:

```bash
sudo systemctl restart nginx
```

---

## 5. 🔒 Allow HTTP Traffic in Google Cloud Firewall

Go to [Google Cloud Console → VPC network → Firewall rules](https://console.cloud.google.com/networking/firewalls) and:

- Add rule to allow **TCP:80** and **TCP:5000** for **all IPs (0.0.0.0/0)**.
- Make sure `default-allow-http` is enabled or create your own.

---

## 6. 🚀 Create Gunicorn Systemd Service

Create service file:

```bash
sudo nano /etc/systemd/system/nopasanadape.service
```

Paste:

```ini
[Unit]
Description=Gunicorn for nopasanadape Flask app
After=network.target

[Service]
User=nopasanadape
Group=www-data
WorkingDirectory=/home/nopasanadape/NoPasaNadaPE/server
ExecStart=/home/nopasanadape/NoPasaNadaPE/server/.venv/bin/gunicorn --workers 3 --bind 10.128.0.4:5000 main:app

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable nopasanadape
sudo systemctl start nopasanadape
```

Check status:

```bash
sudo systemctl status nopasanadape
```

## Useful snippets

Copy DB from VM --> Local Server:
```bash
scp -i ~/.ssh/google_compute_engine -o "IdentitiesOnly=yes" -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" nopasanadape@34.59.226.241:/home/nopasanadape/NoPasaNadaPE/server/data/members.db /home/gfreundt/NoPasaNadaPE/server/data/members.db
```

Copy DB from Local Server --> VM:
```bash
scp -i ~/.ssh/google_compute_engine -o "IdentitiesOnly=yes" -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" /home/gfreundt/NoPasaNadaPE/server/data/members.db nopasanadape@34.59.226.241:/home/nopasanadape/NoPasaNadaPE/server/data/members.db
```

Copy DB from Local Server --> D: Local PC:
```bash
cp /mnt/d/members.db /home/gfreundt/NoPasaNadaPE/server/data/members.db
```

Copy DB from D: Local PC to Local Server:
```bash
cp /mnt/d/members.db /home/gfreundt/NoPasaNadaPE/server/data/members.db
```