"""
Pytest tests for the resolve-ci-vars GitHub Action using ACT CLI.

This module contains parameterized tests that exercise different scenarios
for the resolve-ci-vars action using the ACT CLI wrapper.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from .act_runner import (
    ActRunner,
    WorkflowTrigger,
    create_push_trigger,
    create_pr_trigger,
    create_workflow_dispatch_trigger,
)


STATIC_INPUT_SCENARIOS = [
    ("basic_static", {"username": "testuser", "environment": "development"}),
    ("empty_static", {}),
    ("complex_static", {
        "api_url": "https://api.example.com",
        "timeout": "30",
        "debug": "true"
    }),
]

JINJA_INPUT_SCENARIOS = [
    ("basic_jinja", {"greeting": "'Hello, ' + 'World!'", "answer": "42"}),
    ("conditional_jinja", {"is_prod": "False", "port": "8080 if False else 443"}),
    ("string_operations", {"computed_name": "'test' + '_' + 'user'"}),
]

TRIGGER_SCENARIOS = [
    ("push_main", create_push_trigger(ref="refs/heads/main")),
    ("push_feature", create_push_trigger(ref="refs/heads/feature-branch")),
    ("pr_opened", create_pr_trigger(action="opened")),
    ("pr_synchronize", create_pr_trigger(action="synchronize")),
    ("workflow_dispatch_basic", create_workflow_dispatch_trigger()),
    ("workflow_dispatch_with_pr", create_workflow_dispatch_trigger(inputs={"pr": "5"})),
]


@pytest.fixture
def act_runner() -> ActRunner:
    """Create an ActRunner instance for testing."""
    repo_root = Path(__file__).parent.parent
    return ActRunner(repo_dir=repo_root)


@pytest.fixture
def available_workflows(act_runner: ActRunner) -> list[str]:
    """Get list of available workflow files."""
    return act_runner.list_workflows()


def test_act_runner_initialization(act_runner: ActRunner):
    """Test that ActRunner initializes correctly."""
    assert act_runner.repo_dir.exists()
    assert act_runner.action_file.exists()
    assert act_runner.act_binary == "act"
    assert act_runner.default_image == "catthehacker/ubuntu:act-latest"


def test_list_workflows(act_runner: ActRunner, available_workflows: list[str]):
    """Test that we can list available workflows."""
    assert len(available_workflows) > 0
    assert "test-action.yml" in available_workflows


@pytest.mark.parametrize("scenario_name,static_inputs", STATIC_INPUT_SCENARIOS)
def test_static_inputs(
    act_runner: ActRunner,
    scenario_name: str,
    static_inputs: Dict[str, str]
):
    """Test resolve-ci-vars action with different static input scenarios."""
    trigger = create_push_trigger()
    
    static_inputs_str = "\n".join([f"{k}={v}" for k, v in static_inputs.items()])
    
    action_inputs = {
        "static_inputs": static_inputs_str,
        "log_outputs": "true"
    }
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        job_name="test-resolve-vars",
        dry_run=True,
        verbose=True
    )
    
    assert result.success, f"Static inputs scenario {scenario_name} failed: {result.stderr}"
    
    assert "test-resolve-vars" in result.stdout or "test-resolve-vars" in result.stderr


@pytest.mark.parametrize("scenario_name,jinja_inputs", JINJA_INPUT_SCENARIOS)
def test_jinja_inputs(
    act_runner: ActRunner,
    scenario_name: str,
    jinja_inputs: Dict[str, str]
):
    """Test resolve-ci-vars action with different Jinja2 expression scenarios."""
    trigger = create_push_trigger()
    
    jinja_inputs_str = "\n".join([f"{k}={v}" for k, v in jinja_inputs.items()])
    
    action_inputs = {
        "jinja_inputs": jinja_inputs_str,
        "log_outputs": "true"
    }
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        job_name="test-resolve-vars",
        dry_run=True,
        verbose=True
    )
    
    assert result.success, f"Jinja inputs scenario {scenario_name} failed: {result.stderr}"
    
    assert "test-resolve-vars" in result.stdout or "test-resolve-vars" in result.stderr


@pytest.mark.parametrize("scenario_name,trigger", TRIGGER_SCENARIOS)
def test_trigger_scenarios(
    act_runner: ActRunner,
    scenario_name: str,
    trigger: WorkflowTrigger
):
    """Test resolve-ci-vars action with different trigger scenarios."""
    action_inputs = {
        "static_inputs": "test_var=test_value",
        "log_outputs": "true"
    }
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        job_name="test-resolve-vars",
        dry_run=True,
        verbose=True
    )
    
    assert result.success, f"Trigger scenario {scenario_name} failed: {result.stderr}"
    
    assert trigger.event_name in result.stdout or trigger.event_name in result.stderr


def test_standard_ci_variables(act_runner: ActRunner):
    """Test that standard CI variables are resolved correctly."""
    trigger = create_pr_trigger(action="opened", pr_number=5)
    
    action_inputs = {
        "log_outputs": "true"
    }
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        job_name="test-resolve-vars",
        dry_run=True,
        verbose=True
    )
    
    assert result.success, f"Standard CI variables test failed: {result.stderr}"
    
    assert "pull_request" in result.stdout or "pull_request" in result.stderr


def test_workflow_dispatch_with_pr_input(act_runner: ActRunner):
    """Test workflow_dispatch with PR input auto-detection."""
    trigger = create_workflow_dispatch_trigger(inputs={"pr": "5"})
    
    action_inputs = {
        "log_outputs": "true"
    }
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        job_name="test-resolve-vars",
        dry_run=True,
        verbose=True
    )
    
    assert result.success, f"Workflow dispatch with PR input failed: {result.stderr}"
    
    assert "workflow_dispatch" in result.stdout or "workflow_dispatch" in result.stderr


def test_combined_inputs(act_runner: ActRunner):
    """Test resolve-ci-vars action with both static and Jinja inputs."""
    trigger = create_push_trigger()
    
    action_inputs = {
        "static_inputs": "username=testuser\nenvironment=development",
        "jinja_inputs": "greeting='Hello, ' + 'World!'\nanswer=42",
        "log_outputs": "true"
    }
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        job_name="test-resolve-vars",
        dry_run=True,
        verbose=True
    )
    
    assert result.success, f"Combined inputs test failed: {result.stderr}"
    
    assert "test-resolve-vars" in result.stdout or "test-resolve-vars" in result.stderr


def test_invalid_workflow_file(act_runner: ActRunner):
    """Test handling of invalid workflow file."""
    trigger = create_push_trigger()
    
    with pytest.raises(FileNotFoundError):
        act_runner.test_action(
            workflow_file="nonexistent.yml",
            trigger=trigger
        )


def test_timeout_handling(act_runner: ActRunner):
    """Test that the ActRunner has proper timeout handling."""
    assert hasattr(act_runner, 'test_action')
    
    trigger = create_push_trigger()
    action_inputs = {"log_outputs": "true"}
    
    result = act_runner.test_action(
        workflow_file="test-action.yml",
        trigger=trigger,
        action_inputs=action_inputs,
        dry_run=True
    )
    
    assert "timed out" not in result.stderr


def test_different_platforms(act_runner: ActRunner):
    """Test running action on different platforms."""
    platforms = [
        ("ubuntu-latest", "catthehacker/ubuntu:act-latest"),
        ("ubuntu-20.04", "catthehacker/ubuntu:act-20.04"),
    ]
    
    for platform, image in platforms:
        trigger = create_push_trigger()
        trigger.platform = platform
        trigger.image = image
        
        action_inputs = {"log_outputs": "true"}
        
        result = act_runner.test_action(
            workflow_file="test-action.yml",
            trigger=trigger,
            action_inputs=action_inputs,
            job_name="test-resolve-vars",
            dry_run=True
        )
        
        assert result.success, f"Platform {platform} failed: {result.stderr}"
