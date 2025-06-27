# CSO Helper

[![🇬🇧 English](https://flagcdn.com/w40/gb.png)](README.md)
[![🇷🇺 Русский](https://flagcdn.com/w40/ru.png)](/README.ru.md)

**csohelper** is a Telegram bot for the MTUCI dormitory that provides useful reference information: contacts, schedules, services, discount cards, and more.

## Features

* Quick access to dormitory information (address, postal code, manager, commandant, housing office, HR department, dean’s office, clinic, library)
* List of discount cards for popular chains
* Schedules for showers, kitchen, laundry, washing machines
* Cafe menu and timetable
* Information about the current academic week
* List of useful study apps
* Directory of services offered by residents
* Support for commands and inline queries in Russian

## Installation

1. Clone the repository:

  ```sh
  git clone https://github.com/yourusername/csohelper.git
  cd csohelper
  ```

2. Install dependencies:

  ```sh
  pip install poetry
  poetry install
  ```

3. Copy `.env.example` to `.env` and specify the database connection parameters:

  ```sh
  cp .env.example .env
  nano .env
  ```

4. Configure the `storage/config.yaml` file (created automatically on first run).
5. Start the bot:

  ```sh
  docker-compose up -d
  ```

## Project structure

`src/python/` — bot source code
`src/res/locale/ru.yaml` — localization and command texts
`src/res/images/` — images for cards and cafes
`storage/config.yaml` — application configuration
`Dockerfile`, `docker-compose.yml` — containerization and database launch

## Adding commands and texts

All commands and response texts are stored in `src/res/locale/ru.yaml`. To add a new command:

1. Add a description in the `commands` section
2. Add the response text in the `echo_commands` section
3. Implement the handler in `src/python/main.py`

License
MIT

Honestly, I have no idea if anyone actually read this