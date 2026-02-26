"""Unit tests for GoldService and get_goal_service factory.

Covered missing lines
---------------------
* 8        GoldService.__init__
* 11-18    GoldService.reset_goals – calls get_config_service().save_config()
* 22       get_goal_service factory function
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.services.goal_service import GoldService, get_goal_service


# ---------------------------------------------------------------------------
# GoldService.__init__ (line 8)
# ---------------------------------------------------------------------------


def test_gold_service_init_creates_instance():
    """GoldService() should construct without arguments and be usable."""
    service = GoldService()
    assert service is not None
    assert isinstance(service, GoldService)


# ---------------------------------------------------------------------------
# GoldService.reset_goals (lines 11-18)
# ---------------------------------------------------------------------------


def test_reset_goals_calls_save_config():
    """reset_goals must call save_config() on the config service."""
    with patch("todopro_cli.services.goal_service.get_config_service") as mock_get_cfg:
        mock_config_service = MagicMock()
        mock_get_cfg.return_value = mock_config_service

        service = GoldService()
        service.reset_goals()

        mock_get_cfg.assert_called_once()
        mock_config_service.save_config.assert_called_once()


def test_reset_goals_calls_get_config_service_each_time():
    """reset_goals should call get_config_service every time it is invoked."""
    with patch("todopro_cli.services.goal_service.get_config_service") as mock_get_cfg:
        mock_config_service = MagicMock()
        mock_get_cfg.return_value = mock_config_service

        service = GoldService()
        service.reset_goals()
        service.reset_goals()

        assert mock_get_cfg.call_count == 2
        assert mock_config_service.save_config.call_count == 2


def test_reset_goals_does_not_raise_when_save_config_succeeds():
    """reset_goals should complete without raising when save_config succeeds."""
    with patch("todopro_cli.services.goal_service.get_config_service") as mock_get_cfg:
        mock_get_cfg.return_value = MagicMock()
        service = GoldService()
        # Should not raise
        service.reset_goals()


# ---------------------------------------------------------------------------
# get_goal_service factory (line 22)
# ---------------------------------------------------------------------------


def test_get_goal_service_returns_gold_service_instance():
    """get_goal_service() must return a GoldService instance."""
    service = get_goal_service()
    assert isinstance(service, GoldService)


def test_get_goal_service_returns_new_instance_each_call():
    """get_goal_service() is a simple factory – each call returns a fresh object."""
    s1 = get_goal_service()
    s2 = get_goal_service()
    assert s1 is not s2
