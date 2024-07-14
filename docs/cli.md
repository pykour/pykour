# Pykour CLI

Pykour CLIは、Pykourアプリケーションを提供したり、Pykourプロジェクトを管理したりするために使用できるコマンドラインプログラムです。
Pykourをインストールすると、ターミナルにpykourコマンドが追加されます。

Pykourアプリケーションを実行するために、`pykour dev`コマンドを使用します。

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

`pykour dev`コマンドを実行すると、Pykourアプリケーションを開発モードで実行します。
デフォルトでは、`auto-reload`が有効になっており、コードを変更するとサーバーが自動的にリロードされます。これはリソースを大量に消費し、安定性が
低下するため、開発モードでのみ使用するべきです。
デフォルトでは、IPアドレス`127.0.0.1`および`8000`ポートでリッスンし、ローカルマシンからのみアクセス可能です。IPアドレスやポートを変更する必要が
ある場合は、`--host`および`--port`オプションを使用できます。

### `pykour run`

```bash
$ pykour run main:app
```

`pykour run`コマンドを実行すると、Pykourアプリケーションを本番モードで実行します。
`auto-reload`がデフォルトでは無効になっているため、コードを変更してもサーバーはリロードされません。
デフォルトでは、IPアドレス`0.0.0.0`および`8000`ポートでリッスンし、どのIPアドレスからでもアクセス可能です。IPアドレスやポートを変更する必要が
ある場合は、`--host`および`--port`オプションを使用できます。
