# Pykour CLI

The Pykour CLI is a command-line program that can be used to serve Pykour applications and manage Pykour projects. 
Once you install Pykour, the pykour command is added to your terminal.

To run a Pykour application, use the `pykour dev` command.

```bash
$ pykour dev main:app
INFO:     Will watch for changes in these directories: ['/home/user/pykour-demo']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [59894] using StatReload
INFO:     Started server process [59896]
INFO:     Waiting for application startup.
INFO:     ASGI 'lifespan' protocol appears unsupported.
INFO:     Application startup complete.
```

### `pykour dev`

```bash
$ pykour dev main:app
```

Running the `pykour dev` command executes the Pykour application in development mode. 

By default, **auto-reload** is enabled, so the server automatically reloads when code changes.
This mode consumes a lot of resources and reduces stability, so it should only be used in development.

By default, it listens on IP address `127.0.0.1` and port `8000`, making it accessible only from the local machine. 
If you need to change the IP address or port, you can use the `--host` and `--port` options.

### `pykour run`

```bash
$ pykour run main:app
```

Running the `pykour run` command executes the Pykour application in production mode.
**Auto-reload** is disabled by default, so the server will not reload when code changes.

By default, it listens on IP address `0.0.0.0` and port `8000`, making it accessible from any IP address.
If you need to change the IP address or port, you can use the `--host` and `--port` options.