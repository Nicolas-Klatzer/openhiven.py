![openhiven.py](https://socialify.git.ci/Luna-Klatzer/openhiven.py/image?description=1&font=Source%20Code%20Pro&forks=1&issues=1&language=1&logo=https%3A%2F%2Fraw.githubusercontent.com%2FLuna-Klatzer%2Fdocs_openhiven.py%2Fmain%2Fdocs%2Fassets%2Fimages%2Fopenhivenpy.png&owner=1&pattern=Floating%20Cogs&pulls=1&stargazers=1&theme=Light)

# [Content](#content)

- [The Hiven API-Wrapper](#the-hiven-api-wrapper-openhivenpy)
    - [Dependencies](#dependencies)
    - [Installation](#installation)
        - [Install (PyPi Release)](#install-pypi-release)
        - [Install (PyPi Specific Version)](#install-pypi-specific-version)
        - [Install (Github Build)](#install-github-build)
    - [Documentation](#documentation)
        - [Usage Example (v0.1.3.2)](#usage-example-v0132)
    - [Development](#development)
        - [Testing](#testing)
        - [Building](#building)
        - [Uploading to PyPi and testing using `twine`](#uploading-to-pypi-and-testing-using-twine)
    - [Contributors](#contributors)
    - [Copyright and License](#copyright-and-license)

# The Hiven API-Wrapper `openhiven.py`

<p align="center">

[![PyPI version](https://badge.fury.io/py/openhivenpy.svg)](https://badge.fury.io/py/openhivenpy)
[![Python Version](https://img.shields.io/badge/python->=3.7-blue?logo=python)](https://python.org)
![Build](https://img.shields.io/github/workflow/status/Luna-Klatzer/openhiven.py/CodeQL?logo=github)
![Lines of Code](https://img.shields.io/tokei/lines/github/Luna-Klatzer/openhiven.py)
[![License](https://img.shields.io/github/license/Luna-Klatzer/openhiven.py)](https://github.com/Luna-Klatzer/openhiven.py/blob/main/LICENSE)
![Coverage](./pytest/coverage.svg)
[![codecov](https://codecov.io/gh/Luna-Klatzer/openhiven.py/branch/main/graph/badge.svg?token=36ADSJZ6F3)](https://codecov.io/gh/Luna-Klatzer/openhiven.py)

</p>

## Dependencies

[![aiohttp](https://img.shields.io/github/pipenv/locked/dependency-version/Luna-Klatzer/openhiven.py/aiohttp/main)](https://docs.aiohttp.org/en/stable/)
[![asyncio](https://img.shields.io/github/pipenv/locked/dependency-version/Luna-Klatzer/openhiven.py/asyncio/main)](https://docs.python.org/3/library/asyncio.html)
[![typing](https://img.shields.io/github/pipenv/locked/dependency-version/Luna-Klatzer/openhiven.py/typing/main)](https://docs.python.org/3/library/typing.html)

## Installation
### Install (PyPi Release)

```bash
python3 -m pip install -U openhivenpy
```

### Install (PyPi Specific Version)

```bash
python3 -m pip install -U openhivenpy==version
```

### Install (Github Build)
```bash
python3 -m pip install -U https://github.com/Luna-Klatzer/openhiven.py/archive/main.zip
```

## Documentation

For full documentation visit the documentation our github pages build
[here](https://Luna-Klatzer.github.io/docs_openhiven.py/)

### Usage Example (v0.2.dev1)

*The following listeners will not pass args to the listener until 0.2.dev2:*

- house_join
- house_remove
- house_update
- house_delete
- house_downtime
- room_create
- room_update
- room_delete
- house_member_join
- house_member_leave
- house_member_enter
- house_member_exit
- house_member_update
- house_member_chunk
- batch_house_member_update
- house_entity_update
- relationship_update
- presence_update
- message_create
- message_update
- message_delete
- typing_start

**A simple UserClient Bot for quick usage:**

```python

import openhivenpy as hiven

client = hiven.UserClient()

@client.event()
async def on_ready():
    print("Bot is ready")

client.run("Insert token")

```

**A simple CommandListener for reacting to commands:**

```python 

import openhivenpy as hiven

client = hiven.UserClient()

@client.event()
async def on_ready():
    print("Bot is ready")

@client.event()
async def on_message_create(msg):
    if msg.content.startswith("-"):
        if msg.content == "-ping":
            return await msg.room.send("pong")

client.run("Insert token")
 
```

**Inherited HivenClient Example:**

```python 

import openhivenpy as hiven

class Bot(hiven.UserClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print("Bot is ready!")

if __name__ == '__main__':
    client = Bot()
    client.run("Insert token")

```

## Development

### Testing

Testing openhiven.py is done over GitHub Actions and more specific `pytest`,
which runs tests for the module that are located in `./pytest`.

These tests validate functionality and also make requests to the Hiven API or
rather in this case a Mock API to not spam the native Rest API of Hiven.
(Visible here: https://mockapi.io/projects/61143430cba40600170c1e66)

*To run these tests simply use (Make sure the pypi module `pytest` is
installed):*

```bash
cd ./pytest
pytest -q --token=<HIVEN_TOKEN>
```

*A HIVEN_TOKEN is required for testing. Get one before running the tests, so
they can run successfully. More
info [here](https://luna-klatzer.github.io/docs_openhiven.py/latest/getting_started/deploying_your_first_bot.html#getting-a-user-token)*

### Building

Building the module to be able to install it can be done using the `build`
module of Python. Simply install `build` and then use this snippet to build the
module:

```bash
python -m build
```

The build module/s should be located in `./dist`

### Uploading to PyPi and testing using `twine`

To upload a new version to PyPi simply use the pypi module `twine`.

Before uploading [build](#building) the module and then test them using:

```bash
twine check dist/*
```

If everything is fine upload using:

```bash
twine upload dist/*
```

## Contributors

<a href="https://github.com/Nicolas-Klatzer/openhiven.py/graphs/contributors"><image src="https://contributors-img.web.app/image?repo=Nicolas-Klatzer/openhiven.py"></a>

## Copyright and License

![License](https://img.shields.io/github/license/Luna-Klatzer/openhiven.py?color=cyan)

Copyright (c) 2021, Nicolas
Klatzer[*](#legal-name-which-does-not-match-the-preferred-and-commonly-used-name-luna-klatzer)
. All rights reserved.

See the [LICENSE](./LICENSE) for information on terms & conditions for usage

###### *Legal name, which does not match the preferred and commonly used name Luna Klatzer
