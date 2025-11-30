import abc
import logging
import subprocess
import os
from typing import List, Optional
import docker
from src.core.config import settings

logger = logging.getLogger(__name__)

class StreamController(abc.ABC):
    @abc.abstractmethod
    def restart_stream(self) -> bool:
        pass

    @abc.abstractmethod
    def stop_stream(self) -> bool:
        pass

    @abc.abstractmethod
    def start_stream(self) -> bool:
        pass

    @abc.abstractmethod
    def get_logs(self, lines: int = 100) -> List[str]:
        pass

class DockerStreamController(StreamController):
    def __init__(self):
        self.client = docker.from_env()
        self.container_name = settings.STREAM_CONTAINER_NAME

    def _get_container(self):
        try:
            return self.client.containers.get(self.container_name)
        except docker.errors.NotFound:
            logger.error(f"Container {self.container_name} not found")
            return None

    def restart_stream(self) -> bool:
        container = self._get_container()
        if container:
            container.restart()
            return True
        return False

    def stop_stream(self) -> bool:
        container = self._get_container()
        if container:
            container.stop()
            return True
        return False

    def start_stream(self) -> bool:
        container = self._get_container()
        if container:
            container.start()
            return True
        return False

    def get_logs(self, lines: int = 100) -> List[str]:
        container = self._get_container()
        if container:
            logs = container.logs(tail=lines).decode('utf-8')
            return logs.split('\n')
        return []

class SystemdStreamController(StreamController):
    def __init__(self):
        self.service_name = settings.STREAM_SERVICE_NAME

    def _run_command(self, command: List[str]) -> bool:
        try:
            subprocess.run(command, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            return False

    def restart_stream(self) -> bool:
        return self._run_command(["sudo", "systemctl", "restart", self.service_name])

    def stop_stream(self) -> bool:
        return self._run_command(["sudo", "systemctl", "stop", self.service_name])

    def start_stream(self) -> bool:
        return self._run_command(["sudo", "systemctl", "start", self.service_name])

    def get_logs(self, lines: int = 100) -> List[str]:
        try:
            result = subprocess.run(
                ["journalctl", "-u", self.service_name, "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True
            )
            return result.stdout.split('\n')
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return []

def get_stream_controller() -> StreamController:
    if settings.STREAM_CONTROLLER_TYPE == "docker":
        return DockerStreamController()
    else:
        return SystemdStreamController()
