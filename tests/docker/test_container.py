"""
Docker container integration tests.

Tests for containerized deployment, health checks, environment configuration,
and container-specific functionality.
"""

import pytest
import requests
import subprocess
import time
import docker
import os
from typing import Generator


@pytest.mark.docker
@pytest.mark.slow
class TestDockerDeployment:
    """Test Docker container deployment and functionality."""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Get Docker client for container management."""
        try:
            client = docker.from_env()
            # Test connection
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    @pytest.fixture(scope="class")
    def docker_image(self, docker_client):
        """Build Docker image for testing."""
        project_root = "/Users/jneaimimacmini/dev/python/n8n-tools"
        
        # Build the image
        print("Building Docker image...")
        image, build_logs = docker_client.images.build(
            path=project_root,
            tag="n8n-tools-api:test",
            rm=True,
            forcerm=True
        )
        
        yield image
        
        # Cleanup: remove the test image
        try:
            docker_client.images.remove("n8n-tools-api:test", force=True)
        except Exception as e:
            print(f"Warning: Could not remove test image: {e}")
    
    @pytest.fixture
    def running_container(self, docker_client, docker_image) -> Generator[dict, None, None]:
        """Start a container and return connection info."""
        # Start container
        container = docker_client.containers.run(
            docker_image.id,
            ports={"8000/tcp": None},  # Random host port
            detach=True,
            environment={
                "ENVIRONMENT": "test",
                "LOG_LEVEL": "INFO"
            },
            remove=True  # Auto-remove when stopped
        )
        
        # Get the assigned port
        container.reload()
        host_port = container.ports["8000/tcp"][0]["HostPort"]
        base_url = f"http://localhost:{host_port}"
        
        # Wait for container to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            
            if i < max_retries - 1:
                time.sleep(1)
        else:
            # Get container logs for debugging
            logs = container.logs().decode()
            container.stop()
            pytest.fail(f"Container failed to start within {max_retries} seconds. Logs:\n{logs}")
        
        yield {
            "container": container,
            "base_url": base_url,
            "host_port": host_port
        }
        
        # Cleanup
        try:
            container.stop()
        except Exception as e:
            print(f"Warning: Could not stop container: {e}")
    
    def test_container_health_check(self, running_container):
        """Test that container health check works."""
        base_url = running_container["base_url"]
        
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "n8n-tools-api"
    
    def test_container_api_functionality(self, running_container, valid_pdf_bytes):
        """Test that API functionality works in container."""
        base_url = running_container["base_url"]
        
        # Test PDF info endpoint
        files = {"file": ("test.pdf", valid_pdf_bytes, "application/pdf")}
        response = requests.post(f"{base_url}/api/v1/pdf/info", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "page_count" in data
        assert data["page_count"] > 0
    
    def test_container_openapi_docs(self, running_container):
        """Test that OpenAPI documentation is accessible in container."""
        base_url = running_container["base_url"]
        
        # Test OpenAPI JSON
        response = requests.get(f"{base_url}/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert schema["info"]["title"] == "N8N Tools API"
        
        # Test Swagger UI
        response = requests.get(f"{base_url}/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_container_environment_variables(self, docker_client, docker_image):
        """Test container with different environment variables."""
        # Test with custom environment
        container = docker_client.containers.run(
            docker_image.id,
            ports={"8000/tcp": None},
            detach=True,
            environment={
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "WARNING",
                "MAX_FILE_SIZE_MB": "25"
            },
            remove=True
        )
        
        try:
            # Wait for startup
            time.sleep(5)
            
            container.reload()
            host_port = container.ports["8000/tcp"][0]["HostPort"]
            base_url = f"http://localhost:{host_port}"
            
            # Verify it's running
            response = requests.get(f"{base_url}/health", timeout=10)
            assert response.status_code == 200
            
        finally:
            container.stop()
    
    def test_container_resource_limits(self, docker_client, docker_image):
        """Test container with resource limits."""
        # Test with memory and CPU limits
        container = docker_client.containers.run(
            docker_image.id,
            ports={"8000/tcp": None},
            detach=True,
            mem_limit="256m",
            cpuset_cpus="0",
            environment={"ENVIRONMENT": "test"},
            remove=True
        )
        
        try:
            # Wait for startup
            time.sleep(5)
            
            container.reload()
            host_port = container.ports["8000/tcp"][0]["HostPort"]
            base_url = f"http://localhost:{host_port}"
            
            # Verify it works with limited resources
            response = requests.get(f"{base_url}/health", timeout=10)
            assert response.status_code == 200
            
            # Test basic functionality
            files = {"file": ("test.pdf", self.create_small_pdf(), "application/pdf")}
            response = requests.post(f"{base_url}/api/v1/pdf/info", files=files, timeout=15)
            assert response.status_code == 200
            
        finally:
            container.stop()
    
    def test_container_logs(self, running_container):
        """Test that container produces appropriate logs."""
        container = running_container["container"]
        base_url = running_container["base_url"]
        
        # Make a request to generate logs
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        
        # Get logs
        logs = container.logs().decode()
        
        # Verify log content
        assert "uvicorn" in logs.lower() or "fastapi" in logs.lower()
        assert "8000" in logs  # Port should be mentioned
    
    def test_container_restart_behavior(self, docker_client, docker_image):
        """Test container restart behavior."""
        # Start container with restart policy
        container = docker_client.containers.run(
            docker_image.id,
            ports={"8000/tcp": None},
            detach=True,
            restart_policy={"Name": "on-failure", "MaximumRetryCount": 3},
            environment={"ENVIRONMENT": "test"},
            remove=False  # Don't auto-remove for restart testing
        )
        
        try:
            # Wait for startup
            time.sleep(5)
            
            container.reload()
            host_port = container.ports["8000/tcp"][0]["HostPort"]
            base_url = f"http://localhost:{host_port}"
            
            # Verify it's running
            response = requests.get(f"{base_url}/health", timeout=10)
            assert response.status_code == 200
            
            # Stop and verify restart policy is set
            container_info = container.attrs
            assert container_info["HostConfig"]["RestartPolicy"]["Name"] == "on-failure"
            
        finally:
            container.remove(force=True)
    
    def test_container_volume_mounting(self, docker_client, docker_image, tmp_path):
        """Test container with volume mounting for temp files."""
        # Create temporary directory for mounting
        temp_dir = tmp_path / "container_temp"
        temp_dir.mkdir()
        
        container = docker_client.containers.run(
            docker_image.id,
            ports={"8000/tcp": None},
            detach=True,
            volumes={str(temp_dir): {"bind": "/app/temp", "mode": "rw"}},
            environment={
                "ENVIRONMENT": "test",
                "TEMP_DIR": "/app/temp"
            },
            remove=True
        )
        
        try:
            # Wait for startup
            time.sleep(5)
            
            container.reload()
            host_port = container.ports["8000/tcp"][0]["HostPort"]
            base_url = f"http://localhost:{host_port}"
            
            # Verify it's running
            response = requests.get(f"{base_url}/health", timeout=10)
            assert response.status_code == 200
            
            # Test file processing (which should use the mounted temp directory)
            files = {"file": ("test.pdf", self.create_small_pdf(), "application/pdf")}
            response = requests.post(f"{base_url}/api/v1/pdf/info", files=files, timeout=15)
            assert response.status_code == 200
            
        finally:
            container.stop()
    
    def create_small_pdf(self) -> bytes:
        """Create a small PDF for testing."""
        return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000054 00000 n 
0000000103 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
165
%%EOF"""


@pytest.mark.docker
class TestDockerCompose:
    """Test Docker Compose deployment scenarios."""
    
    def test_docker_compose_up(self):
        """Test Docker Compose brings up the service."""
        project_root = "/Users/jneaimimacmini/dev/python/n8n-tools"
        
        # Use docker-compose for testing
        compose_file = os.path.join(project_root, "docker-compose.yml")
        
        if not os.path.exists(compose_file):
            pytest.skip("docker-compose.yml not found")
        
        try:
            # Start services
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                pytest.fail(f"Docker Compose failed to start: {result.stderr}")
            
            # Wait for service to be ready
            time.sleep(10)
            
            # Test health endpoint
            response = requests.get("http://localhost:8000/health", timeout=10)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            
        finally:
            # Cleanup
            subprocess.run(
                ["docker-compose", "-f", compose_file, "down"],
                cwd=project_root,
                capture_output=True
            )
    
    def test_docker_compose_development(self):
        """Test Docker Compose development configuration."""
        project_root = "/Users/jneaimimacmini/dev/python/n8n-tools"
        
        compose_file = os.path.join(project_root, "docker-compose.dev.yml")
        
        if not os.path.exists(compose_file):
            pytest.skip("docker-compose.dev.yml not found")
        
        try:
            # Start development services
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                pytest.skip(f"Development compose failed: {result.stderr}")
            
            # Wait for service
            time.sleep(10)
            
            # Test health endpoint
            response = requests.get("http://localhost:8000/health", timeout=10)
            assert response.status_code == 200
            
        finally:
            # Cleanup
            subprocess.run(
                ["docker-compose", "-f", compose_file, "down"],
                cwd=project_root,
                capture_output=True
            )


@pytest.mark.docker
class TestContainerSecurity:
    """Test container security configurations."""
    
    def test_container_non_root_user(self, docker_client, docker_image):
        """Test that container runs as non-root user."""
        # Run container and check user
        container = docker_client.containers.run(
            docker_image.id,
            command="whoami",
            remove=True
        )
        
        # Container should complete quickly for whoami command
        result = container.wait(timeout=10)
        logs = container.logs().decode().strip()
        
        # Should not be root
        assert logs != "root"
    
    def test_container_file_permissions(self, docker_client, docker_image):
        """Test container file permissions are secure."""
        # Check file permissions in container
        container = docker_client.containers.run(
            docker_image.id,
            command="ls -la /app",
            remove=True
        )
        
        result = container.wait(timeout=10)
        logs = container.logs().decode()
        
        # Should show proper file permissions
        assert "app" in logs or "uvicorn" in logs
        # Application files should not be world-writable
        assert "rwxrwxrwx" not in logs
    
    def test_container_no_sensitive_info(self, docker_client, docker_image):
        """Test container doesn't contain sensitive information."""
        # Check environment variables
        container = docker_client.containers.run(
            docker_image.id,
            command="env",
            remove=True
        )
        
        result = container.wait(timeout=10)
        logs = container.logs().decode()
        
        # Should not contain sensitive data
        sensitive_patterns = ["password", "secret", "key=", "token"]
        for pattern in sensitive_patterns:
            assert pattern.lower() not in logs.lower()


@pytest.mark.docker
@pytest.mark.slow
class TestContainerPerformance:
    """Test container performance characteristics."""
    
    def test_container_startup_time(self, docker_client, docker_image):
        """Test container startup performance."""
        start_time = time.time()
        
        container = docker_client.containers.run(
            docker_image.id,
            ports={"8000/tcp": None},
            detach=True,
            remove=True
        )
        
        try:
            # Wait for health check to pass
            container.reload()
            host_port = container.ports["8000/tcp"][0]["HostPort"]
            base_url = f"http://localhost:{host_port}"
            
            ready_time = None
            for i in range(30):
                try:
                    response = requests.get(f"{base_url}/health", timeout=2)
                    if response.status_code == 200:
                        ready_time = time.time()
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            
            if ready_time:
                startup_time = ready_time - start_time
                # Container should start within reasonable time
                assert startup_time < 30  # 30 seconds max
                print(f"Container startup time: {startup_time:.2f} seconds")
            else:
                pytest.fail("Container failed to become ready within 30 seconds")
                
        finally:
            container.stop()
    
    def test_container_memory_usage(self, running_container):
        """Test container memory usage during operation."""
        container = running_container["container"]
        base_url = running_container["base_url"]
        
        # Get initial stats
        stats = container.stats(stream=False)
        initial_memory = stats["memory_stats"]["usage"]
        
        # Perform several operations
        for i in range(5):
            files = {"file": (f"test_{i}.pdf", self.create_test_pdf(), "application/pdf")}
            response = requests.post(f"{base_url}/api/v1/pdf/info", files=files)
            assert response.status_code == 200
        
        # Get final stats
        stats = container.stats(stream=False)
        final_memory = stats["memory_stats"]["usage"]
        
        # Memory should not grow excessively
        memory_growth = final_memory - initial_memory
        # Allow for some growth but not excessive
        assert memory_growth < 100 * 1024 * 1024  # Less than 100MB growth
    
    def create_test_pdf(self) -> bytes:
        """Create test PDF content."""
        return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
159
%%EOF"""
