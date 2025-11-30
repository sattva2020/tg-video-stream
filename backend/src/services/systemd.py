import os
import subprocess
import logging
import sys
from typing import Optional
from sqlalchemy.orm import Session
from src.models.telegram import Channel
from src.services.encryption import EncryptionService

logger = logging.getLogger(__name__)

class SystemdService:
    def __init__(self, db: Session):
        self.db = db
        self.encryption_service = EncryptionService()
        # Configuration
        # In production, these should be set correctly via env vars
        self.service_dir = os.getenv("SYSTEMD_SERVICE_DIR", "/etc/systemd/system")
        self.env_dir = os.getenv("STREAMER_ENV_DIR", "/etc/telegram-streamer/env")
        self.streamer_dir = os.getenv("STREAMER_DIR", "/opt/telegram-streamer")
        self.python_exec = sys.executable # Use the same python interpreter

    def _get_service_name(self, channel_id: str) -> str:
        return f"streamer-{channel_id}.service"

    def _get_env_file_path(self, channel_id: str) -> str:
        return os.path.join(self.env_dir, f"{channel_id}.env")

    def _is_linux(self) -> bool:
        return sys.platform.startswith("linux")

    def generate_service_file(self, channel_id: str) -> str:
        env_file = self._get_env_file_path(channel_id)
        
        content = f"""[Unit]
Description=Telegram Streamer for Channel {channel_id}
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={self.streamer_dir}
EnvironmentFile={env_file}
ExecStart={self.python_exec} -m streamer.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        return content

    def create_env_file(self, channel: Channel):
        if not self._is_linux():
            logger.warning("Not on Linux, skipping env file creation in /etc/...")
            return

        env_file = self._get_env_file_path(str(channel.id))
        try:
            os.makedirs(os.path.dirname(env_file), exist_ok=True)
            
            session_string = self.encryption_service.decrypt_session(channel.account.encrypted_session)
            api_id = os.getenv("API_ID", "")
            api_hash = os.getenv("API_HASH", "")
            
            # Simple port allocation strategy or disable metrics for now
            # prometheus_port = 9090 + (channel.chat_id % 1000) 
            
            content = f"""API_ID={api_id}
API_HASH={api_hash}
SESSION_STRING={session_string}
CHAT_ID={channel.chat_id}
CHANNEL_ID={channel.id}
VIDEO_QUALITY={channel.video_quality or '720p'}
LOOP=1
# PROMETHEUS_PORT=...
"""
            with open(env_file, "w") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to create env file: {e}")
            raise

    def install_service(self, channel: Channel):
        if not self._is_linux():
            logger.warning("Not on Linux, skipping service installation")
            return

        service_name = self._get_service_name(str(channel.id))
        service_path = os.path.join(self.service_dir, service_name)
        
        content = self.generate_service_file(str(channel.id))
        
        try:
            with open(service_path, "w") as f:
                f.write(content)
            
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "enable", service_name], check=True)
        except Exception as e:
            logger.error(f"Failed to install service {service_name}: {e}")
            raise

    def start_channel(self, channel_id: str):
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise ValueError("Channel not found")
            
        if self._is_linux():
            self.create_env_file(channel)
            self.install_service(channel)
            
            service_name = self._get_service_name(channel_id)
            subprocess.run(["systemctl", "start", service_name], check=True)
        else:
            logger.info(f"Mock start channel {channel_id} (Windows/Dev)")

        channel.status = "running"
        self.db.commit()

    def stop_channel(self, channel_id: str):
        if self._is_linux():
            service_name = self._get_service_name(channel_id)
            subprocess.run(["systemctl", "stop", service_name], check=True)
        else:
            logger.info(f"Mock stop channel {channel_id} (Windows/Dev)")
        
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            channel.status = "stopped"
            self.db.commit()

    def restart_channel(self, channel_id: str):
        self.stop_channel(channel_id)
        self.start_channel(channel_id)
