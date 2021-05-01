import os
import pathlib
import time

import pytest

from flytekit.common import launch_plan
from flytekit.models.core.identifier import Identifier, ResourceType
from flytekit.models import literals

PROJECT = "flytesnacks"
VERSION = os.getpid()


@pytest.fixture(scope="session")
def flyte_workflows_source():
    return pathlib.Path(os.path.dirname(__file__)) / "mock_flyte_repo"


@pytest.fixture(scope="session")
def flyte_workflows_register(flyte_workflows_source):
    os.execute(
        f"flytectl register files -p {PROJECT}"
    )


def test_stub(flyteclient, flyte_workflows_register):
    projects = flyteclient.list_projects_paginated(limit=5, token=None)
    assert len(projects) <= 5


def test_launch_workflow(flyteclient, flyte_workflows_register):
    lp = launch_plan.SdkLaunchPlan.fetch(
        "flytesnacks", "development", "workflows.hello_world.my_wf", f"v{os.getpid()}"
    )
    execution = lp.launch_with_literals(
        "flytesnacks", "development", literals.LiteralMap({})
    )
    print(execution.id.name)
