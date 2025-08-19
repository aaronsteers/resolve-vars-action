"""
ACT CLI wrapper for testing the resolve-ci-vars GitHub Action locally.

This module provides a clean Python interface for testing the resolve-ci-vars action
using the nektos/act CLI tool with pytest parameterized tests.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class ActResult:
    """Result of running an ACT CLI command."""
    
    returncode: int
    stdout: str
    stderr: str
    success: bool = field(init=False)
    
    def __post_init__(self) -> None:
        self.success = self.returncode == 0


@dataclass
class WorkflowTrigger:
    """Configuration for triggering a GitHub Actions workflow."""
    
    event_name: str
    event_payload: Dict[str, Any] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    platform: str = "ubuntu-latest"
    image: str = "catthehacker/ubuntu:act-latest"  # Medium size option


class ActRunner:
    """
    Python wrapper around the nektos/act CLI for testing the resolve-ci-vars action.
    
    This class provides a clean interface for running the action with different
    trigger scenarios and event payloads.
    """
    
    def __init__(
        self,
        repo_dir: Union[str, Path],
        act_binary: str = "act",
        default_image: str = "catthehacker/ubuntu:act-latest"
    ):
        """
        Initialize the ACT runner for resolve-ci-vars action testing.
        
        Args:
            repo_dir: Path to resolve-ci-vars-action repository root
            act_binary: Path to act CLI binary (default: "act" from PATH)
            default_image: Default Docker image to use (medium size)
        """
        self.repo_dir = Path(repo_dir)
        self.act_binary = act_binary
        self.default_image = default_image
        
        self.action_file = self.repo_dir / "action.yml"
        if not self.action_file.exists():
            raise FileNotFoundError(f"Action file not found: {self.action_file}")
        
        try:
            result = subprocess.run(
                [self.act_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"ACT CLI not available: {result.stderr}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"ACT CLI not found or not working: {e}")
    
    def test_action(
        self,
        workflow_file: str,
        trigger: WorkflowTrigger,
        action_inputs: Optional[Dict[str, Any]] = None,
        job_name: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False
    ) -> ActResult:
        """
        Test the resolve-ci-vars action using ACT CLI.
        
        Args:
            workflow_file: Name of test workflow file (e.g., "test-action.yml")
            trigger: Workflow trigger configuration
            action_inputs: Inputs to pass to the resolve-ci-vars action
            job_name: Specific job to run (optional)
            dry_run: Only show what would be run
            verbose: Enable verbose output
            
        Returns:
            ActResult with execution details
        """
        cmd = [self.act_binary]
        
        cmd.append(trigger.event_name)
        
        workflow_path = self.repo_dir / ".github" / "workflows" / workflow_file
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
        
        cmd.extend(["-W", str(workflow_path)])
        
        cmd.extend(["-P", f"{trigger.platform}={trigger.image}"])
        
        if job_name:
            cmd.extend(["-j", job_name])
        
        if dry_run:
            cmd.append("--dryrun")
        
        if verbose:
            cmd.append("-v")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as event_file:
            json.dump(trigger.event_payload, event_file, indent=2)
            event_file_path = event_file.name
        
        try:
            if trigger.event_payload:
                cmd.extend(["-e", event_file_path])
            
            for key, value in trigger.secrets.items():
                cmd.extend(["-s", f"{key}={value}"])
            
            env = {}
            for key, value in trigger.env_vars.items():
                env[key] = value
            
            if action_inputs:
                for key, value in action_inputs.items():
                    env[f"INPUT_{key.upper().replace('-', '_')}"] = str(value)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env={**os.environ, **env} if env else None
            )
            
            return ActResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            return ActResult(
                returncode=-1,
                stdout="",
                stderr="Command timed out after 5 minutes"
            )
        finally:
            Path(event_file_path).unlink(missing_ok=True)
    
    def list_workflows(self) -> List[str]:
        """List available workflow files."""
        workflows_dir = self.repo_dir / ".github" / "workflows"
        if not workflows_dir.exists():
            return []
        
        return [
            f.name for f in workflows_dir.glob("*.yml")
            if f.is_file()
        ]


def create_push_trigger(
    ref: str = "refs/heads/main",
    sha: str = "abc123",
    repository_name: str = "resolve-ci-vars-action",
    repository_owner: str = "aaronsteers",
    **kwargs: Any
) -> WorkflowTrigger:
    """Create a push event trigger for resolve-ci-vars action testing."""
    payload = {
        "ref": ref,
        "after": sha,
        "before": "000000",
        "repository": {
            "name": repository_name,
            "full_name": f"{repository_owner}/{repository_name}",
            "owner": {"login": repository_owner}
        },
        **kwargs
    }
    return WorkflowTrigger(event_name="push", event_payload=payload)


def create_pr_trigger(
    action: str = "opened",
    pr_number: int = 1,
    base_ref: str = "main",
    head_ref: str = "feature-branch",
    repository_name: str = "resolve-ci-vars-action",
    repository_owner: str = "aaronsteers",
    **kwargs: Any
) -> WorkflowTrigger:
    """Create a pull request event trigger for resolve-ci-vars action testing."""
    payload = {
        "action": action,
        "number": pr_number,
        "pull_request": {
            "number": pr_number,
            "base": {"ref": base_ref},
            "head": {"ref": head_ref},
            "title": "Test PR",
            "body": "Test PR body"
        },
        "repository": {
            "name": repository_name,
            "full_name": f"{repository_owner}/{repository_name}",
            "owner": {"login": repository_owner}
        },
        **kwargs
    }
    return WorkflowTrigger(event_name="pull_request", event_payload=payload)


def create_workflow_dispatch_trigger(
    inputs: Optional[Dict[str, Any]] = None,
    repository_name: str = "resolve-ci-vars-action",
    repository_owner: str = "aaronsteers",
    **kwargs: Any
) -> WorkflowTrigger:
    """Create a workflow_dispatch event trigger for resolve-ci-vars action testing."""
    payload = {
        "inputs": inputs or {},
        "repository": {
            "name": repository_name,
            "full_name": f"{repository_owner}/{repository_name}",
            "owner": {"login": repository_owner}
        },
        **kwargs
    }
    return WorkflowTrigger(event_name="workflow_dispatch", event_payload=payload)
