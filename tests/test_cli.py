import pytest
from unittest import mock
import sys
from pykour.cli import parse_args, main, usage_text


def test_parse_args_run_command():
    args = parse_args(["run", "main:app"])
    assert args.command == "run"
    assert args.app == "main:app"
    assert args.host == "0.0.0.0"
    assert args.port == 8000
    assert args.reload is False
    assert args.workers == 1


def test_parse_args_run_command_with_options():
    args = parse_args(["run", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload", "--workers", "4"])
    assert args.command == "run"
    assert args.app == "main:app"
    assert args.host == "0.0.0.0"
    assert args.port == 8080
    assert args.reload is True
    assert args.workers == 4


def test_parse_args_version():
    with pytest.raises(SystemExit):
        parse_args(["-v"])


def test_parse_args_help(capsys):
    args = parse_args(["-h"])
    assert args.help is True


@mock.patch("pykour.cli.uvicorn.run")
@mock.patch("pykour.cli.sys.exit")
def test_main_run_command(mock_exit, mock_uvicorn_run):
    with mock.patch.object(sys, "argv", ["cli.py", "run", "main:app"]):
        main()
        mock_uvicorn_run.assert_called_once_with(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=1,
            server_header=False,
        )
        mock_exit.assert_not_called()


@mock.patch("pykour.cli.sys.exit")
def test_main_help_command(mock_exit):
    with mock.patch.object(sys, "argv", ["cli.py", "-h"]):
        with mock.patch("builtins.print") as mock_print:
            main()
            mock_print.assert_called_once_with(usage_text)
            mock_exit.assert_called_once_with(0)


@mock.patch("pykour.cli.sys.exit")
def test_main_invalid_command(mock_exit):
    with mock.patch.object(sys, "argv", ["cli.py", "invalid"]):
        with mock.patch("builtins.print") as mock_print:
            main()
            mock_print.assert_called_once_with(usage_text)
            mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    pytest.main()
