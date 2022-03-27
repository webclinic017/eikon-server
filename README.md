<div align="center">
    <h1>OpenCTA Eikon Server</h1>
</div>


# Features

- REST API for Refinitiv Eikon
- Secured with API key
- TLS encryption


# Quick Start

## Pre-requisites

Set up a Windows server. You can rent one at [Time4VPS](https://time4vps.com/).

On the Windows server:

- Install [Refinitiv Eikon](https://eikon.thomsonreuters.com/index.html).
- Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
- Install [Cygwin](http://cygwin.com/install.html).


## Installation

On the Windows server:

- Clone the repo:

```bash
git clone https://github.com/OpenCTA-com/eikon-server.git
cd eikon-server
```

- Create a conda environment and install the packages:

```bash
conda create -n python3 python=3.8
conda activate python3
pip install -r requirements.txt
```

- Duplicate `template.env` to `.env`.
- Edit the configuration file `.env` and set your own environment variables values replacing the `{{ XXX }}` placeholders.


## TLS encryption (optional)

If you want to use TLS encryption (which is recommended), you need to generate SSL certificates:

- Update your DNS registry (in our case, on https://domains.google.com/registrar/opencta.com/dns) to make a sub domain (`eikon.opencta.com` in our case) point to the Windows server.

On a Linux/MacOS machine:

- Install certbot:
  - MacOS: `brew install certbot`
  - Ubuntu: `sudo apt install certbot` 
- Run:

```bash
certbot -d eikon.opencta.com --manual --logs-dir certbot --config-dir certbot --work-dir certbot --preferred-challenges dns certonly
```

- Copy the following files to the Windows server in the `certificates` folder:
  - `certbot/live/eikon.opencta.com/fullchain.pem`
  - `certbot/live/eikon.opencta.com/privkey.pem`


## Server launch

On the Windows server:

- Open the [port 80](https://windowsreport.com/open-firewall-ports/).


```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 80 \
  --ssl-keyfile ./certificates/privkey.pem \ # only if you created SSL certificates
  --ssl-certfile ./certificates/fullchain.pem \ # only if you created SSL certificates
  --lifespan on
```

## Usage

Now you should be able to query data with:

```bash
curl -H "Authorization: $EIKON_SECRET_KEY" \
  https://eikon.opencta.com/data/IBM,GOOG.O/TR.PriceClose,TR.Volume/
```

You can access the API documentation from the Internet: https://eikon.opencta.com/docs.


# Notes

This service is not dockerized because it needs to run on Windows and unfortunately the host networking driver is not supported on Docker Desktop for Windows or Docker EE for Windows Server.