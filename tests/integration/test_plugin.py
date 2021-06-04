import os
import pathlib
import time
import subprocess

import pytest

from flytekit.common import launch_plan
from flytekit.models.core.identifier import Identifier, ResourceType
from flytekit.models import literals

PROJECT = "flytesnacks"
DOMAIN = "development"
VERSION = os.getpid()


@pytest.fixture(scope="session")
def flyte_workflows_source_dir():
    return pathlib.Path(os.path.dirname(__file__)) / "mock_flyte_repo"


@pytest.fixture(scope="session")
def flyte_workflows_register(request):
    if request.config.getoption("--proto-path"):
        proto_path = request.config.getoption("--proto-path")
        subprocess.check_call(
            f"flytectl register files {proto_path} -p {PROJECT} -d {DOMAIN} -v {VERSION} --archive",
            shell=True,
        )
    else:
        docker_compose = request.getfixturevalue("docker_compose")
        docker_compose.execute(
            f"exec -w /flyteorg/src -e SANDBOX=1 -e PROJECT={PROJECT} -e VERSION=v{VERSION} "
            "backend make -C workflows register"
        )


def test_stub(flyteclient, flyte_workflows_register):
    projects = flyteclient.list_projects_paginated(limit=5, token=None)
    assert len(projects) <= 5


def test_launch_workflow(request, flyteclient, flyte_workflows_register):
    if request.config.getoption("--proto-path"):
        subprocess.check_call(
            f"flytectl get launchplan -p {PROJECT} -d {DOMAIN} core.flyte_basics.hello_world.my_wf --version {VERSION} --execFile execution_spec_{VERSION}.yaml",
            shell=True,
        )
        execution_name = subprocess.check_output(
            f"flytectl create execution --execFile execution_spec_{VERSION}.yaml -p {PROJECT} -d {DOMAIN}",
            shell=True,
        )
        print(execution_name)
    else:
        lp = launch_plan.SdkLaunchPlan.fetch(
            "flytesnacks",
            "development",
            "workflows.hello_world.my_wf",
            f"v{os.getpid()}",
        )
        execution = lp.launch_with_literals(
            "flytesnacks", "development", literals.LiteralMap({})
        )
        print(execution.id.name)
