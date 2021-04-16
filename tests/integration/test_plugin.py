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
def flyte_workflows_source_dir():
    return pathlib.Path(os.path.dirname(__file__)) / "mock_flyte_repo"


@pytest.fixture(scope="session")
def flyte_workflows_register(docker_compose):
    docker_compose.execute(
        f"exec -w /flyteorg/src -e SANDBOX=1 -e PROJECT={PROJECT} -e VERSION=v{VERSION} "
        "backend make -C workflows register"
    )


# see https://github.com/flyteorg/pytest-flyte/pull/4/checks?check_run_id=2366114378
@pytest.mark.skip(reason="doesn't work on CI yet")
def test_stub(flyteclient, flyte_workflows_register):
    projects = flyteclient.list_projects_paginated(limit=5, token=None)
    assert len(projects) <= 5


@pytest.mark.skip(reason="doesn't work on CI yet")
def test_launch_workflow(flyteclient, flyte_workflows_register):
    lp = launch_plan.SdkLaunchPlan.fetch(
        "flytesnacks", "development", "workflows.basic.hello_world.my_wf", f"v{os.getpid()}"
    )
    execution = lp.launch_with_literals(
        "flytesnacks", "development", literals.LiteralMap({})
    )
    print(execution.id.name)
