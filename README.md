# CSO Helper

[![🇺🇸 English](https://flagcdn.com/w40/us.png)](README.md)
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

2. Copy `.env.example` to `.env` and specify the database connection parameters:

  ```sh
  cp .env.example .env
  nano .env
  ```

3. First start bot
    #### Via Docker
    ```sh
    docker compose up
    ```
    #### Without docker
    Install
    ```sh
    pip install poetry
    poetry install
    ```
    Start
    ```sh
    poetry run csohelper
    ```

4. Configure the `storage/config.yaml` file (created automatically on first run).

5. Retry start bot:
    #### Docker
    ```sh
    docker compose up
    ```
    #### Poetry
    ```sh
    poetry run csohelper
    ```

## Project structure

`src/python/` — bot source code<br>
`src/res/locale/ru.yaml` — localization and command texts<br>
`src/res/images/` — images for cards and cafés<br>
`storage/config.yaml` — application configuration<br>
`Dockerfile`, `docker-compose.yml` — containerization and database launch

## Adding commands and texts

All commands and response texts are stored in `src/res/locale/ru.yaml`. To add a new command:

1. Add a description in the `commands` section
2. Add the response text in the `echo_commands` section
3. Implement the handler

License
MIT

Honestly, I have no idea if anyone actually read this