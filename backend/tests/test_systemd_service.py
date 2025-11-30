import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.services.systemd import SystemdService
from src.models.telegram import Channel, TelegramAccount
import uuid
import sys

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def systemd_service(mock_db):
    with patch("src.services.systemd.EncryptionService") as MockEncryption:
        service = SystemdService(mock_db)
        service.encryption_service.decrypt_session.return_value = "decrypted_session"
        return service

def test_generate_service_file(systemd_service):
    channel_id = str(uuid.uuid4())
    content = systemd_service.generate_service_file(channel_id)
    assert f"Description=Telegram Streamer for Channel {channel_id}" in content
    assert "ExecStart=" in content
    assert "EnvironmentFile=" in content

@patch("src.services.systemd.os.makedirs")
@patch("src.services.systemd.open", new_callable=mock_open)
@patch("src.services.systemd.os.getenv")
def test_create_env_file(mock_getenv, mock_file, mock_makedirs, systemd_service):
    # Force linux platform for this test
    with patch("src.services.systemd.sys.platform", "linux"):
        mock_getenv.side_effect = lambda k, d="": {"API_ID": "123", "API_HASH": "abc"}.get(k, d)
        
        channel = MagicMock(spec=Channel)
        channel.id = uuid.uuid4()
        channel.chat_id = 123456789
        channel.video_quality = "1080p"
        channel.account = MagicMock(spec=TelegramAccount)
        channel.account.encrypted_session = "encrypted"
        
        systemd_service.create_env_file(channel)
        
        mock_file.assert_called()
        handle = mock_file()
        handle.write.assert_called()
        content = handle.write.call_args[0][0]
        assert "API_ID=123" in content
        assert "SESSION_STRING=decrypted_session" in content
        assert "CHAT_ID=123456789" in content
        assert f"CHANNEL_ID={channel.id}" in content

@patch("src.services.systemd.subprocess.run")
@patch("src.services.systemd.open", new_callable=mock_open)
def test_start_channel(mock_file, mock_subprocess, systemd_service):
    with patch("src.services.systemd.sys.platform", "linux"):
        channel_id = str(uuid.uuid4())
        channel = MagicMock(spec=Channel)
        channel.id = uuid.UUID(channel_id)
        channel.status = "stopped"
        
        systemd_service.db.query.return_value.filter.return_value.first.return_value = channel
        
        # Mock create_env_file and install_service to avoid file ops in this test
        with patch.object(systemd_service, 'create_env_file') as mock_create_env, \
             patch.object(systemd_service, 'install_service') as mock_install:
            
            systemd_service.start_channel(channel_id)
            
            mock_create_env.assert_called_once_with(channel)
            mock_install.assert_called_once_with(channel)
            mock_subprocess.assert_called()
            assert channel.status == "running"
            systemd_service.db.commit.assert_called()
