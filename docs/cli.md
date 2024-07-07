# Pykour CLI

Pykour CLI is a command line program that you can use to serve your Pykour application, manage your Pykour project, 
and more.

When you install Pykour, it adds a pykour command to your terminal.

```bash
$ pykour run main:app
```

### `pykour run`

By default, pykour run executes in production mode.

It will listen on the IP address `0.0.0.0`, making it accessible from any IP address. This default setting ensures that 
your application is available on your local network. If you need to change the IP address or port, you can use the 
`--host` and `--port` options:

```bash
$ pykour run main:app --host 127.0.0.1 --port 8080
```
