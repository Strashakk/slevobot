import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import requests

from cogs.rizky import Rizky


@pytest.fixture
def rizky_cog():
    """Create a Rizky cog instance with a mocked bot."""
    mock_bot = MagicMock()
    return Rizky(mock_bot)


@pytest.fixture
def mock_interaction():
    """Create a mocked Discord interaction."""
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.response.is_done = False
    interaction.followup = AsyncMock()
    return interaction


class TestSendDiscounts:
    """Tests for the _send_discounts method."""

    @pytest.mark.asyncio
    async def test_send_discounts_success_with_results(
        self, rizky_cog, mock_interaction
    ):
        """Test successful scraping with discount results."""
        mock_results = [
            {
                "obchod": "Test Shop",
                "cena": "100 Kč",
                "sleva": "-20%",
                "platnost": "do 30. 4. 2026",
            }
        ]

        with patch.object(rizky_cog, "_scrape_discounts", return_value=mock_results):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        # Verify response was sent
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "🔥 **Test Product" in call_args
        assert "Test Shop" in call_args
        assert "100 Kč" in call_args
        assert "-20%" in call_args

        # Verify no followup messages for single chunk
        mock_interaction.followup.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_discounts_no_results(
        self, rizky_cog, mock_interaction
    ):
        """Test when no discounts are found - should show empty_text message."""
        with patch.object(rizky_cog, "_scrape_discounts", return_value=[]):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        # Should send the empty_text message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert call_args == "No discounts found."

    @pytest.mark.asyncio
    async def test_send_discounts_request_exception(
        self, rizky_cog, mock_interaction
    ):
        """Test handling of requests.RequestException."""
        with patch.object(
            rizky_cog, "_scrape_discounts", side_effect=requests.RequestException("Connection error")
        ):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "Error occurred: Connection error" == call_args

    @pytest.mark.asyncio
    async def test_send_discounts_value_error(
        self, rizky_cog, mock_interaction
    ):
        """Test handling of ValueError."""
        with patch.object(
            rizky_cog, "_scrape_discounts", side_effect=ValueError("Invalid URL")
        ):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "Error occurred: Invalid URL" == call_args

    @pytest.mark.asyncio
    async def test_send_discounts_type_error(
        self, rizky_cog, mock_interaction
    ):
        """Test handling of TypeError."""
        with patch.object(
            rizky_cog, "_scrape_discounts", side_effect=TypeError("Wrong type")
        ):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "Error occurred: Wrong type" == call_args

    @pytest.mark.asyncio
    async def test_send_discounts_attribute_error(
        self, rizky_cog, mock_interaction
    ):
        """Test handling of AttributeError."""
        with patch.object(
            rizky_cog, "_scrape_discounts", side_effect=AttributeError("Missing attribute")
        ):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "Error occurred: Missing attribute" == call_args

    @pytest.mark.asyncio
    async def test_send_discounts_multiple_chunks(
        self, rizky_cog, mock_interaction
    ):
        """Test message splitting into multiple chunks."""
        # Create many results to exceed chunk size
        mock_results = [
            {
                "obchod": f"Shop {i}",
                "cena": f"{i * 100} Kč",
                "sleva": f"-{i}%",
                "platnost": f"do {i}. 4. 2026",
            }
            for i in range(100)
        ]

        with patch.object(rizky_cog, "_scrape_discounts", return_value=mock_results):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Test Product",
                empty_text="No discounts found.",
                error_text="Error occurred",
                url="https://example.com",
                emoji="🔥",
            )

        # Should send first chunk via response and rest via followup
        mock_interaction.response.send_message.assert_called_once()
        assert mock_interaction.followup.send.call_count >= 1

    @pytest.mark.asyncio
    async def test_send_discounts_correct_parameters_passed(
        self, rizky_cog, mock_interaction
    ):
        """Test that all parameters are correctly used."""
        mock_results = [
            {
                "obchod": "Shop",
                "cena": "50 Kč",
                "sleva": "-10%",
                "platnost": "dnes",
            }
        ]

        with patch.object(rizky_cog, "_scrape_discounts", return_value=mock_results):
            await rizky_cog._send_discounts(
                interaction=mock_interaction,
                title="Custom Title",
                empty_text="Empty message",
                error_text="Custom error",
                url="https://custom-url.com",
                emoji="🎯",
            )

        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "🎯 **Custom Title" in call_args
        assert "Shop" in call_args
        assert "50 Kč" in call_args


class TestScrapeDiscounts:
    """Tests for the _scrape_discounts method."""

    def create_mock_response(self, html_content: str) -> MagicMock:
        """Helper to create a mocked requests response."""
        mock_response = MagicMock()
        mock_response.content = html_content.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        return mock_response

    def test_scrape_discounts_success_single_item(self, rizky_cog):
        """Test successful scraping with a single discount item."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Test Shop">Shop</a>
                </span>
                <strong class="discount_price_value">100 Kc</strong>
                <div class="discount_percentage">-20%</div>
                <div class="discounts_validity">do 30. 12. 2030</div>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 1
        assert results[0]["obchod"] == "Test Shop"
        assert results[0]["cena"] == "100 Kc"
        assert results[0]["sleva"] == "-20%"
        assert results[0]["platnost"] == "do 30. 12. 2030"

    def test_scrape_discounts_success_multiple_items(self, rizky_cog):
        """Test successful scraping with multiple discount items."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop A">A</a>
                </span>
                <strong class="discount_price_value">50 Kc</strong>
                <div class="discount_percentage">-10%</div>
                <div class="discounts_validity">do 25. 12. 2030</div>
            </div>
            <div class="discount_row" id="d2">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop B">B</a>
                </span>
                <strong class="discount_price_value">75 Kc</strong>
                <div class="discount_percentage">-15%</div>
                <div class="discounts_validity">do 28. 12. 2030</div>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 2
        assert results[0]["obchod"] == "Shop A"
        assert results[1]["obchod"] == "Shop B"

    def test_scrape_discounts_no_results(self, rizky_cog):
        """Test when no discount rows are found."""
        html = "<html><body>No discounts here</body></html>"
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert results == []

    def test_scrape_discounts_duplicate_ids_filtered(self, rizky_cog):
        """Test that duplicate discount IDs are filtered out."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop A">A</a>
                </span>
                <strong class="discount_price_value">50 Kc</strong>
                <div class="discount_percentage">-10%</div>
                <div class="discounts_validity">do 25. 12. 2030</div>
            </div>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop A Duplicate">Dup</a>
                </span>
                <strong class="discount_price_value">999 Kc</strong>
                <div class="discount_percentage">-99%</div>
                <div class="discounts_validity">do 1. 1. 2031</div>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 1
        assert results[0]["obchod"] == "Shop A"

    def test_scrape_discounts_missing_fields(self, rizky_cog):
        """Test handling of missing optional fields."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <strong class="discount_price_value">100 Kč</strong>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 1
        assert results[0]["obchod"] == ""
        assert results[0]["cena"] == "100 Kč"
        assert results[0]["sleva"] == ""
        assert results[0]["platnost"] == ""

    def test_scrape_discounts_missing_price_defaults(self, rizky_cog):
        """Test that missing price defaults to 'neuvedeno'."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop">Shop</a>
                </span>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 1
        assert results[0]["cena"] == "neuvedeno"

    def test_scrape_discounts_dnes_konci_handling(self, rizky_cog):
        """Test special handling for 'dnes končí' validity text."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop">Shop</a>
                </span>
                <strong class="discount_price_value">100 Kč</strong>
                <div class="discount_percentage">-20%</div>
                <div class="discounts_validity">dnes končí</div>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 1
        assert "končí dnes" in results[0]["platnost"]

    def test_scrape_discounts_request_exception(self, rizky_cog):
        """Test handling of requests.RequestException."""
        with patch("requests.get", side_effect=requests.RequestException("Connection failed")):
            with pytest.raises(requests.RequestException):
                rizky_cog._scrape_discounts("https://example.com")

    def test_scrape_discounts_timeout(self, rizky_cog):
        """Test handling of request timeout."""
        with patch("requests.get", side_effect=requests.Timeout("Request timed out")):
            with pytest.raises(requests.Timeout):
                rizky_cog._scrape_discounts("https://example.com")

    def test_scrape_discounts_http_error(self, rizky_cog):
        """Test handling of HTTP errors via raise_for_status."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                rizky_cog._scrape_discounts("https://example.com")

    def test_scrape_discounts_nbsp_replacement(self, rizky_cog):
        """Test that non-breaking spaces are replaced with regular spaces."""
        html = """
        <html>
            <div class="discount_row" id="d1">
                <span class="discounts_shop_name">
                    <a class="product_link_history" title="Shop">Shop</a>
                </span>
                <strong class="discount_price_value">100&nbsp;Kč</strong>
                <div class="discount_percentage">-20&nbsp;%</div>
                <div class="discounts_validity">do&nbsp;30.&nbsp;4.&nbsp;2026</div>
            </div>
        </html>
        """
        mock_response = self.create_mock_response(html)

        with patch("requests.get", return_value=mock_response):
            results = rizky_cog._scrape_discounts("https://example.com")

        assert len(results) == 1
        assert "\xa0" not in results[0]["cena"]
        assert "\xa0" not in results[0]["sleva"]
        assert "\xa0" not in results[0]["platnost"]
