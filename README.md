# Hryaks Telegram Bot

## Installation

#### Docker installing

* Install Docker

Arch-Based systems:

```shell      
sudo pacman -S docker docker-compose && sudo systemctl enable docker && sudo systemctl start docker && mkdir ShTP && git clone https://github.com/ITClassDev/Docker ShTP/Docker && git clone https://github.com/ITClassDev/Backend ShTP/Backend && git clone https://github.com/ITClassDev/FrontEnd ShTP/Frontend
```

Debian-based systems:

```shell
sudo apt update && sudo apt install apt-transport-https ca-certificates curl software-properties-common -fy && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable" -y && sudo apt install docker docker-compose -fy && sudo systemctl enable docker && sudo systemctl start docker && mkdir ShTP && git clone https://github.com/ITClassDev/Docker ShTP/Docker && git clone https://github.com/ITClassDev/Backend ShTP/Backend && git clone https://github.com/ITClassDev/FrontEnd ShTP/Frontend
```

* Clone repo and go to folder (command will be work if GH account already logged in)

```shell
git clone https://github.com/slavapmk/hryaks-bot hryaks && cd hryaks
```

* Run `docker-compose up` - it will automatically download, build and prepare bot env

```shell
docker-compose up
```

* Insert to `storage/tokens.json` file telegram token from [BotFather](https://t.me/BotFather)

```shell
nano storage/tokens.json
```

* Retry `docker-compose up` for run

```shell
docker-compose up
```

#### Manual install

* Install Python 3.10+

  _For example from [here](https://www.python.org/downloads/release/python-3120/)_
* Install Poetry (more detailed [here](https://python-poetry.org/docs/))

```shell
curl -sSL https://install.python-poetry.org | python3 -
```

* Install poetry dependencies

```shell
poetry install
```

* Run poetry "start" task

```shell
poetry run hryaks
```

After first run program will create `storage` folder with `tokens.json` and `db.sqlite` files. Insert telegram token
from [BotFather](https://t.me/BotFather)