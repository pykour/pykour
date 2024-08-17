import pytest
import os
from pykour.cli import main, parse_args


def test_version_argument_displays_version(mocker):
    mocker.patch("sys.argv", ["pykour", "-v"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0


def test_help_argument_displays_help(mocker):
    mocker.patch("sys.argv", ["pykour", "-h"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0


def test_dev_command_runs_uvicorn(mocker):
    mocker.patch("sys.argv", ["pykour", "dev", "main:app"])
    mock_run = mocker.patch("uvicorn.run")
    main()
    mock_run.assert_called_once_with(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        workers=1,
        server_header=False,
    )


def test_run_command_runs_uvicorn(mocker):
    mocker.patch("sys.argv", ["pykour", "run", "main:app"])
    mock_run = mocker.patch("uvicorn.run")
    main()
    mock_run.assert_called_once_with(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=os.cpu_count() * 2 + 1,
        server_header=False,
    )


def test_invalid_command_displays_usage(mocker):
    mocker.patch("sys.argv", ["pykour", "invalid"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_parse_args_dev_command():
    args = parse_args(["dev", "main:app"])
    assert args.command == "dev"
    assert args.app == "main:app"
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.reload is True
    assert args.workers == 1


def test_parse_args_run_command():
    args = parse_args(["run", "main:app"])
    assert args.command == "run"
    assert args.app == "main:app"
    assert args.host == "0.0.0.0"
    assert args.port == 8000
    assert args.reload is False
    assert args.workers == (os.cpu_count() * 2) + 1
