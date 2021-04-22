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


@pytest.hookimpl(tryfirst=True)
def pytest_addhooks(pluginmanager):
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
    d = pathlib.Path(pytestconfig.rootdir) / ".pytest_flyte"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d)


@pytest.fixture(scope="session")
def kustomization_file(template_cache):
    template = TEMPLATE_ENV.get_template("kustomization.yaml.tmpl")
    contents = template.render()
    checksum = hashlib.md5(contents.encode()).hexdigest()

    with open(template_cache / f"kustomization-{checksum}.yaml", "w") as handle:
        print(contents, file=handle)
        handle.seek(0)
        yield handle.name


@pytest.fixture(scope="session")
def flyte_workflows_source_dir(pytestconfig):
    return str(pytestconfig.rootdir)


@pytest.fixture(scope="session")
def flyte_workflows_register(docker_compose):
    docker_compose.execute("exec backend -w /flyteorg/src make register")


@pytest.fixture(scope="session")
def docker_compose(docker_compose_file, docker_compose_project_name, capsys_suspender):

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
def docker_compose_file(flyte_workflows_source_dir, kustomization_file, template_cache):
    with open(template_cache / "docker-compose.yaml", "w") as handle:
        template = TEMPLATE_ENV.get_template("docker-compose.yaml.tmpl")
        print(
            template.render(
                build_context_dir=os.path.join(PROJECT_ROOT, "docker"),
                flyte_workflows_source_dir=flyte_workflows_source_dir,
                kustomization_file_path=kustomization_file,
            ),
            file=handle,
        )
        handle.seek(0)
        yield handle.name


@pytest.fixture(scope="session")
def docker_cleanup():
    return "version"


@pytest.fixture(scope="session")
def flyteclient(docker_ip, docker_services, docker_compose, capsys_suspender):
    port = docker_services.port_for("backend", 30081)
    url = f"{docker_ip}:{port}"
    os.environ["FLYTE_PLATFORM_URL"] = url
    os.environ["FLYTE_PLATFORM_INSECURE"] = "true"

    def _check():
        try:
            docker_compose.execute("exec backend wait-for-flyte.sh")
            return True
        except Exception as e:
            print(e)
            return False

    with capsys_suspender():
        docker_services.wait_until_responsive(timeout=900, pause=1, check=_check)
    return friendly.SynchronousFlyteClient(url, insecure=True)
