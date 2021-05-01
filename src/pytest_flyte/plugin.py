import hashlib
import os
import pathlib
import shutil
from contextlib import contextmanager

import pytest
from flytekit.clients import friendly
from pytest_docker.plugin import DockerComposeExecutor

from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = os.path.dirname(__file__)
TEMPLATE_ENV = Environment(loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "templates")))


def pytest_addoption(parser):
    parser.addoption("--local", action="local", default=False, help="To run in local mode")
    parser.addoption(
        "--flyte-platform-url",
        action="store",
        dest="flyte_platform_url",
        default=None,
        help='Default "name" for hello().',
    )


@pytest.hookimpl(tryfirst=True)
def pytest_addhooks(pluginmanager):
    if pytest.islocal:
        import pytest_docker.plugin

        # make sure docker plugin is registered before flyte so pytest-flyte overrides pytest-docker fixtures
        try:
            pluginmanager.register(pytest_docker.plugin, "docker")
        except ValueError as exc:
            print(f"pytest-docker already registered: {exc}")


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
        capmanager = pytestconfig.pluginmanager.getplugin('capturemanager')
        capmanager.suspend_global_capture(in_=True)
        yield
        capmanager.resume_global_capture()

    return _capsys_suspender


@pytest.fixture(scope="session")
def docker_compose_project_name():
    return "pytest-flyte"


@pytest.fixture(scope="session")
def template_cache(pytestconfig):
    if pytest.islocal:
        d = pathlib.Path(pytestconfig.rootdir) / ".pytest_flyte"
        d.mkdir(parents=True, exist_ok=True)
        yield d
        shutil.rmtree(d)


@pytest.fixture(scope="session")
def kustomization_file(template_cache):
    if pytest.islocal:
        template = TEMPLATE_ENV.get_template("kustomization.yaml.tmpl")
        contents = template.render()
        checksum = hashlib.md5(contents.encode()).hexdigest()

        with open(template_cache / f"kustomization-{checksum}.yaml", "w") as handle:
            print(contents, file=handle)
            handle.seek(0)
            yield handle.name

@pytest.fixture(scope="session")
def flyte_workflows_source(workflow_source):
    return str(workflow_source)


@pytest.fixture(scope="session")
def flyte_workflows_register(flyte_workflows_source):
    # TODO:
    os.execute(f"flytectl register file flyte_workflows_source")


@pytest.fixture(scope="session")
def docker_compose(docker_compose_file, docker_compose_project_name, capsys_suspender):
    if pytest.islocal:
        class _DockerComposeExecutor(DockerComposeExecutor):
            """
            This subclass wraps the DockerComposeExecutor.execute method so that pytest capture sys stdin/out/err
            is suspended whenever docker compose execute is invoked. This is so that the end user doesn't have to
            use capsys_suspender when using this fixture.
            """
            def execute(self, subcommand):
                with capsys_suspender():
                    super().execute(subcommand)

        return _DockerComposeExecutor(docker_compose_file, docker_compose_project_name)


@pytest.fixture(scope="session")
def docker_compose_file(kustomization_file, template_cache):
    if pytest.islocal:
        with open(template_cache / "docker-compose.yaml", "w") as handle:
            template = TEMPLATE_ENV.get_template("docker-compose.yaml.tmpl")
            print(
                template.render(
                    build_context_dir=os.path.join(PROJECT_ROOT, "docker"),
                    kustomization_file_path=kustomization_file,
                ),
                file=handle,
            )
            handle.seek(0)
            yield handle.name


@pytest.fixture(scope="session")
def docker_cleanup():
    return "version"

class Env:
    def __init__(self, url):
        self.flyte_url = url

    def __eq__(self, url):
        return self.flyte_url == url

@pytest.fixture(scope="session")
def env_setup(request, docker_ip, docker_services, docker_compose, capsys_suspender):
    if pytest.islocal:
        port = docker_services.port_for("backend", 30081)

        def _check():
            try:
                docker_compose.execute("exec backend wait-for-flyte.sh")
                return True
            except Exception as e:
                print(e)
                return False

        with capsys_suspender():
            docker_services.wait_until_responsive(timeout=900, pause=1, check=_check)
            return Env(f"{docker_ip}:{port}")
    else:
        flyte_platform_url = request.config.getoption("flyte_platform_url")
        if flyte_platform_url is not None:
            return Env(str(os.environ["FLYTE_PLATFORM_URL"]))
        print("Please set FLYTE_PLATFORM_URL env or run pytest with --local flag")


@pytest.fixture(scope="session")
def flyteclient(request,env_setup):
    pytest.islocal = request.config.getoption("--local")
    if "FLYTE_PLATFORM_INSECURE" not in os.environ:
        os.environ["FLYTE_PLATFORM_INSECURE"] = "true"

    if env_setup.flyte_url != "":
        with capsys_suspender():
            return friendly.SynchronousFlyteClient(env_setup.flyte_url, insecure=bool(os.environ["FLYTE_PLATFORM_INSECURE"]))


