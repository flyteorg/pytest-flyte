import os
import subprocess
from contextlib import contextmanager

import pytest
from flytekit.clients import friendly
from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = os.path.dirname(__file__)
TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "templates"))
)


def pytest_addoption(parser):
    parser.addoption(
        "--local",
        action="store",
        default=True,
        help="Local/Remote",
    )
    parser.addoption(
        "--flyte-platform-url",
        action="store",
        default=None,
        help="Flyte Platform URL",
    )
    parser.addoption(
        "--proto-path",
        action="store",
        default=None,
        help="Serialized Data Proto Path",
    )
    parser.addoption(
        "--source",
        action="store",
        default=None,
        help="Source directory Path",
    )
    parser.addoption(
        "--kustomize",
        action="store",
        default=None,
        help="Kustomize file path",
    )


@pytest.fixture(scope="session")
def capsys_suspender(pytestconfig):
    """
    Returns a context manager that can be used to temporarily suspend global capturing of stderr/stdin/stdout.

    Example:

    def test_something(capsys_suspender):
        print("foo")  # captured
        with capsys_suspender():
            print("bar")  # not captured
        print("baz")  # captured

    """

    @contextmanager
    def _capsys_suspender():
        capmanager = pytestconfig.pluginmanager.getplugin("capturemanager")
        capmanager.suspend_global_capture(in_=True)
        yield
        capmanager.resume_global_capture()

    return _capsys_suspender


@pytest.fixture(scope="session")
def flyte_workflows_register(request):
    proto_path = request.config.getoption("--proto-path")
    subprocess.check_call(f"flytectl register file {proto_path}", shell=True)


@pytest.fixture(scope="session")
def flyteclient(request):
    capsys_suspender = request.getfixturevalue("capsys_suspender")
    version = ""

    if not request.config.getoption("--proto-path"):
        raise ValueError("Serialized Data Proto Path must be set")
    if not request.config.getoption("--source"):
        raise ValueError("Source directory path must be set")
    if request.config.getoption("--version"):
        version = request.config.getoption("--version")

    source = request.config.getoption("--source")
    if request.config.getoption("--local") in ["True", "true", True]:
        sandbox_command = "flytectl sandbox start"
        if len(source) > 0:
            sandbox_command = f"{sandbox_command} --source={source}"
        if len(version) > 0:
            sandbox_command = f"{sandbox_command} --version={version}"

        subprocess.check_call(f"{sandbox_command}", shell=True)

        os.environ["FLYTE_PLATFORM_URL"] = "http://127.0.0.1:30081"
        os.environ["FLYTE_PLATFORM_INSECURE"] = "true"

    else:
        if request.config.getoption("--flyte-platform-url"):
            os.environ["FLYTE_PLATFORM_URL"] = request.config.getoption(
                "--flyte-platform-url"
            )
            os.environ["FLYTE_PLATFORM_INSECURE"] = "true"

        else:
            raise ValueError("Flyte Platform URL must be set")
    with capsys_suspender():
        return friendly.SynchronousFlyteClient(
            os.environ["FLYTE_PLATFORM_URL"],
            insecure=bool(os.environ["FLYTE_PLATFORM_INSECURE"]),
        )