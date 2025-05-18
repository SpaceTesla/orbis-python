import pytest
from pathlib import Path

def test_dockerfile_exists():
    """Test if Dockerfile is generated in the correct location"""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile should exist in the project root"

def test_dockerfile_content():
    """Test if Dockerfile contains essential components"""
    with open("Dockerfile", "r", encoding='utf-8') as f:
        content = f.read()
        
    # Check for essential Dockerfile components
    assert "FROM" in content, "Dockerfile should contain a base image"
    assert "WORKDIR" in content, "Dockerfile should specify a working directory"
    assert "COPY" in content, "Dockerfile should copy application files"
    assert "RUN" in content, "Dockerfile should contain build steps"

def test_docker_build():
    """Test if Docker image can be built successfully"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "build", "-t", "dockerfile-generator:test", "."],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'  # Replace invalid characters instead of raising error
        )
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Docker build failed: {e.stderr}") 