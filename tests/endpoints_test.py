"""Endpoints specification tests."""

from headscale_api.endpoints import ENDPOINTS, Endpoint


def test_endpoint_messages():
    """Test if all endpoints have initialized all messages."""
    for key, endpoint in ENDPOINTS.items():
        assert isinstance(endpoint, Endpoint), f"{key}: value is not an Endpoint."
        assert (
            endpoint.logger_start_message is not None
        ), f"{key}: logger_start_message is not initialized."
        assert (
            endpoint.logger_success_message is not None
        ), f"{key}: logger_success_message is not initialized."
        assert (
            endpoint.logger_fail_message is not None
        ), f"{key}: logger_fail_message is not initialized."


def test_endpoint_formatting():
    """Test if all endpoints have initialized all messages."""
    for endpoint in ENDPOINTS.values():
        endpoint.check_logger_format()
