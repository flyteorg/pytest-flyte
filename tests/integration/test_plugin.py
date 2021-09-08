import os
import subprocess

import pytest
from flytekit.common import launch_plan
from flytekit.models import literals

PROJECT = "flytesnacks"
DOMAIN = "development"
VERSION = os.getpid()

@pytest.fixture(scope="session")
def flyte_workflows_register(request):
    proto_path = request.config.getoption("--proto-path")
    subprocess.check_call(
        f"flytectl register files {proto_path} -p {PROJECT} -d {DOMAIN} --version=v{VERSION}",
        shell=True,
    )


def test_stub(flyteclient, flyte_workflows_register, capsys_suspender):
    with capsys_suspender():
        projects = flyteclient.list_projects_paginated(limit=5, token=None)
        assert projects.__len__() == 2


def test_launch_workflow(flyte_workflows_register):
    lp = launch_plan.SdkLaunchPlan.fetch(
        PROJECT, DOMAIN, "workflows.hello_world.my_wf", f"v{os.getpid()}"
    )
    execution = lp.launch_with_literals(
        PROJECT, DOMAIN, literals.LiteralMap({})
    )
    print(execution.id.name)
