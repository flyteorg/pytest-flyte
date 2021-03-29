import hashlib
import os
import pathlib
import shutil

import pytest
from flytekit.clients import friendly
from pytest_docker.plugin import DockerComposeExecutor

from jinja2 import Environment, PackageLoader

PROJECT_ROOT = os.path.dirname(__file__)
TEMPLATE_ENV = Environment(loader=PackageLoader("pytest_flyte"))


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
def docker_compose(docker_compose_file, docker_compose_project_name):
    return DockerComposeExecutor(docker_compose_file, docker_compose_project_name)


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
def flyteclient(docker_ip, docker_services, docker_compose):
    port = docker_services.port_for("backend", 30081)
    url = f"{docker_ip}:{port}"
    os.environ["FLYTE_PLATFORM_URL"] = url
    os.environ["FLYTE_PLATFORM_INSECURE"] = "true"

    def _check():
        docker_compose.execute("exec backend wait-for-flyte.sh")
        return True

    docker_services.wait_until_responsive(timeout=600, pause=1, check=_check)

    return friendly.SynchronousFlyteClient(url, insecure=True)
