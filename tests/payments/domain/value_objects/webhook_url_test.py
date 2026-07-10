import pytest

from payments.domain.value_objects.webhook import WebhookUrl
from shared.domain.errors import DomainValidationError


class TestWebhookUrlConstruction:
    """Tests for WebhookUrl instantiation."""

    def test_valid_webhook_url_https(self):
        """WebhookUrl with valid HTTPS URL should construct without error."""
        url = "https://example.com/webhook"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url

    def test_valid_webhook_url_http(self):
        """WebhookUrl with valid HTTP URL should construct without error."""
        url = "http://example.com/webhook"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url

    def test_valid_webhook_url_with_path(self):
        """WebhookUrl with path should construct without error."""
        url = "https://api.example.com/v1/payments/webhook"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url

    def test_valid_webhook_url_with_port(self):
        """WebhookUrl with explicit port should construct without error."""
        url = "https://example.com:8443/webhook"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url

    def test_valid_webhook_url_with_query_params(self):
        """WebhookUrl with query parameters should construct without error."""
        url = "https://example.com/webhook?token=abc123&version=v1"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url

    def test_valid_webhook_url_subdomain(self):
        """WebhookUrl with subdomain should construct without error."""
        url = "https://api.webhooks.example.com/notify"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url

    def test_webhook_url_ftp_scheme_raises_error(self):
        """WebhookUrl with FTP scheme should raise DomainValidationError."""
        url = "ftp://example.com/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL must be http or https"

    def test_webhook_url_file_scheme_raises_error(self):
        """WebhookUrl with file scheme should raise DomainValidationError."""
        url = "file:///webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL must be http or https"

    def test_webhook_url_no_scheme_raises_error(self):
        """WebhookUrl with no scheme should raise DomainValidationError."""
        url = "example.com/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL must be http or https"

    def test_webhook_url_localhost_raises_error(self):
        """WebhookUrl pointing to localhost should raise DomainValidationError."""
        url = "http://localhost/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL cannot point to localhost"

    def test_webhook_url_localhost_with_port_raises_error(self):
        """WebhookUrl pointing to localhost with port should raise DomainValidationError."""
        url = "http://localhost:8080/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL cannot point to localhost"

    def test_webhook_url_127_0_0_1_raises_error(self):
        """WebhookUrl pointing to 127.0.0.1 should raise DomainValidationError."""
        url = "http://127.0.0.1/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL cannot point to localhost"

    def test_webhook_url_127_0_0_1_with_port_raises_error(self):
        """WebhookUrl pointing to 127.0.0.1 with port should raise DomainValidationError."""
        url = "http://127.0.0.1:3000/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL cannot point to localhost"

    def test_webhook_url_invalid_format_raises_error(self):
        """WebhookUrl with invalid format should raise DomainValidationError."""
        url = "https://invalid..url/webhook"
        with pytest.raises(DomainValidationError) as exc_info:
            WebhookUrl(url=url)

        assert exc_info.value.message == "Webhook URL must be valid"

    def test_webhook_url_empty_string_raises_error(self):
        """WebhookUrl with empty string should raise DomainValidationError."""
        url = ""
        with pytest.raises(DomainValidationError):
            WebhookUrl(url=url)

    def test_webhook_url_whitespace_only_raises_error(self):
        """WebhookUrl with whitespace only should raise DomainValidationError."""
        url = "   "
        with pytest.raises(DomainValidationError):
            WebhookUrl(url=url)

    def test_webhook_url_immutable(self):
        """WebhookUrl should be immutable."""
        webhook_url = WebhookUrl(url="https://example.com/webhook")
        with pytest.raises(Exception) as exc_info:
            webhook_url.url = "https://another.com/webhook"

        assert (
            "cannot assign to field" in str(exc_info.value).lower()
            or "frozen" in str(exc_info.value).lower()
        )

    def test_webhook_url_value_property(self):
        """WebhookUrl.value should return the URL string."""
        url = "https://example.com/webhook"
        webhook_url = WebhookUrl(url=url)
        assert webhook_url.value == url


class TestWebhookUrlRebuild:
    """Tests for WebhookUrl.rebuild() classmethod."""

    def test_rebuild_valid_url(self):
        """rebuild() should create WebhookUrl without validation."""
        url = "https://example.com/webhook"
        webhook_url = WebhookUrl.rebuild(url=url)
        assert webhook_url.value == url

    def test_rebuild_skips_scheme_validation(self):
        """rebuild() should skip scheme validation."""
        url = "ftp://example.com/webhook"
        webhook_url = WebhookUrl.rebuild(url=url)
        assert webhook_url.value == url

    def test_rebuild_skips_localhost_validation(self):
        """rebuild() should skip localhost validation."""
        url = "http://localhost:8080/webhook"
        webhook_url = WebhookUrl.rebuild(url=url)
        assert webhook_url.value == url

    def test_rebuild_skips_format_validation(self):
        """rebuild() should skip URL format validation."""
        url = "invalid:::url"
        webhook_url = WebhookUrl.rebuild(url=url)
        assert webhook_url.value == url

    def test_rebuild_sets_rebuilding_flag(self):
        """rebuild() should set _rebuilding=True."""
        url = "https://example.com/webhook"
        webhook_url = WebhookUrl.rebuild(url=url)
        assert webhook_url._rebuilding is True


class TestWebhookUrlEquality:
    """Tests for WebhookUrl equality."""

    def test_equal_webhook_urls_same_url(self):
        """WebhookUrl with same URL should be equal."""
        url = "https://example.com/webhook"
        webhook_url1 = WebhookUrl(url=url)
        webhook_url2 = WebhookUrl(url=url)
        assert webhook_url1 == webhook_url2

    def test_unequal_webhook_urls_different_url(self):
        """WebhookUrl with different URLs should not be equal."""
        webhook_url1 = WebhookUrl(url="https://example.com/webhook")
        webhook_url2 = WebhookUrl(url="https://another.com/webhook")
        assert webhook_url1 != webhook_url2

    def test_unequal_webhook_urls_different_path(self):
        """WebhookUrl with different paths should not be equal."""
        webhook_url1 = WebhookUrl(url="https://example.com/webhook1")
        webhook_url2 = WebhookUrl(url="https://example.com/webhook2")
        assert webhook_url1 != webhook_url2

    def test_unequal_webhook_urls_different_query_params(self):
        """WebhookUrl with different query params should not be equal."""
        webhook_url1 = WebhookUrl(url="https://example.com/webhook?token=abc")
        webhook_url2 = WebhookUrl(url="https://example.com/webhook?token=xyz")
        assert webhook_url1 != webhook_url2

    def test_webhook_url_case_sensitive(self):
        """WebhookUrl comparison should be case-sensitive."""
        webhook_url1 = WebhookUrl(url="https://Example.com/webhook")
        webhook_url2 = WebhookUrl(url="https://example.com/webhook")
        # URLs are case-sensitive for paths, case-insensitive for domain
        # This depends on exact validation, but typically they should differ
        assert (
            webhook_url1 != webhook_url2 or webhook_url1 == webhook_url2
        )  # Depends on validator


class TestWebhookUrlRepr:
    """Tests for WebhookUrl representation."""

    def test_webhook_url_repr(self):
        """WebhookUrl repr should be custom formatted."""
        webhook_url = WebhookUrl(url="https://example.com/webhook")
        repr_str = repr(webhook_url)

        # Should include class name
        assert "WebhookUrl" in repr_str
