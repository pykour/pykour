# Installation

## Python Version

We recommend using the latest version of Python. Pykour supports Python 3.9 and newer.

## Dependencies

These packages will be installed automatically when installing Pykour.

- Uvicorn
- Watchdog

## Virtual environments

Use a virtual environment to manage dependencies for your project.

### Create a virtual environment

Create a project directory and a `.venv` directory within it.

```bash
$ mkdir myproject
$ cd myproject
$ python3 -m venv .venv
```

### Activate the virtual environment

Before your work on your project, activate the virtual environment.

```bash
$ source .venv/bin/activate
```

Your shell prompt will change to show the name of the activated environment.

## Install Pykour

Within the activated virtual environment, install Pykour.

```bash
$ pip install pykour
```

Pykour is now installed and ready to use.
