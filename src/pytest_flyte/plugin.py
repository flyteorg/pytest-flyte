import hashlib
import os
import pathlib
import shutil
import subprocess
from contextlib import contextmanager

import pytest
from flytekit.clients import friendly
# from pytest_docker.plugin import DockerComposeExecutor

from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = os.path.dirname(__file__)
TEMPLATE_ENV = Environment(loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "templates")))


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


def execute(command, success_codes=(0,)):
    """Run a shell command."""
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        status = 0
    except subprocess.CalledProcessError as error:
        output = error.output or b""
        status = error.returncode
        command = error.cmd

    if status not in success_codes:
        raise Exception(
            'Command {} returned {}: """{}""".'.format(
                command, status, output.decode("utf-8")
            )
        )

    print(output.decode())
    return output


def str_to_list(arg):
    if isinstance(arg, (list, tuple)):
        return arg
    return [arg]


@pytest.fixture(scope="session")
def docker_compose(docker_compose_file, docker_compose_project_name, capsys_suspender):

    class DockerComposeExecutor:

        def __init__(self, compose_files, compose_project_name):
            self._compose_files = str_to_list(compose_files)
            self._compose_project_name = compose_project_name

        def execute(self, subcommand):
            with capsys_suspender():
                command = "docker-compose"
                for compose_file in self._compose_files:
                    command += ' -f "{}"'.format(compose_file)
                command += ' -p "{}" {}'.format(self._compose_project_name, subcommand)
                return execute(command)
                super().execute(subcommand)

    return DockerComposeExecutor(docker_compose_file, docker_compose_project_name)


@pytest.fixture(scope="session")
def docker_compose_file(flyte_workflows_source_dir, kustomization_file, template_cache):
    with open(template_cache / "docker-compose.yaml", "w") as handle:
        template = TEMPLATE_ENV.get_template("docker-compose.yaml.tmpl")
        rendered_template = template.render(
            build_context_dir=os.path.join(PROJECT_ROOT, "docker"),
            flyte_workflows_source_dir=flyte_workflows_source_dir,
            kustomization_file_path=kustomization_file,
        )
        print(rendered_template)
        print(rendered_template, file=handle)
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
        docker_compose.execute("exec backend wait-for-flyte.sh")
        return True

    with capsys_suspender():
        docker_services.wait_until_responsive(timeout=900, pause=1, check=_check)
        return friendly.SynchronousFlyteClient(url, insecure=True)
