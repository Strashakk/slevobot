import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import requests
from datetime import datetime, timedelta

from cogs.akce import Akce


@pytest.fixture
def akce_cog():
    """Create an Akce cog instance with a mocked bot and mocked scraper."""
    mock_bot = MagicMock()
    cog = Akce(mock_bot)
    # Pre-scrape scraper so calls go to our mock
    cog.scraper = MagicMock()
    return cog


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
    async def test_success_with_results(self, akce_cog, mock_interaction):
        """Successful scrape with discount results."""
        mock_results = [
            {
                "nazev": "Test Shop",
                "cena": "100 Kc",
                "sleva": "-20%",
                "platnost": "do 30. 4. 2026",
            }
        ]
        akce_cog.scraper.scrape.return_value = mock_results

        await akce_cog._send_discounts(
            interaction=mock_interaction,
            title="Test Product",
            empty_text="No discounts found.",
            error_text="Error occurred",
            url="https://example.com",
            emoji="🔥",
        )

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "🔥 **Test Product" in call_args
        assert "Test Shop" in call_args
        assert "100 Kc" in call_args
        assert "-20%" in call_args
        mock_interaction.followup.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_results(self, akce_cog, mock_interaction):
        """No discounts found — shows empty_text."""
        akce_cog.scraper.scrape.return_value = []

        await akce_cog._send_discounts(
            interaction=mock_interaction,
            title="Test Product",
            empty_text="No discounts found.",
            error_text="Error occurred",
            url="https://example.com",
            emoji="🔥",
        )

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert call_args == "No discounts found."

    @pytest.mark.asyncio
    async def test_request_exception(self, akce_cog, mock_interaction):
        """Handles requests.RequestException."""
        akce_cog.scraper.scrape.side_effect = requests.RequestException("Connection error")

        await akce_cog._send_discounts(
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
    async def test_value_error(self, akce_cog, mock_interaction):
        """Handles ValueError."""
        akce_cog.scraper.scrape.side_effect = ValueError("Invalid URL")

        await akce_cog._send_discounts(
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
    async def test_type_error(self, akce_cog, mock_interaction):
        """Handles TypeError."""
        akce_cog.scraper.scrape.side_effect = TypeError("Wrong type")

        await akce_cog._send_discounts(
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
    async def test_attribute_error(self, akce_cog, mock_interaction):
        """Handles AttributeError."""
        akce_cog.scraper.scrape.side_effect = AttributeError("Missing attribute")

        await akce_cog._send_discounts(
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
    async def test_multiple_chunks(self, akce_cog, mock_interaction):
        """Message splitting into multiple chunks."""
        mock_results = [
            {
                "nazev": f"Shop {i}",
                "cena": f"{i * 100} Kc",
                "sleva": f"-{i}%",
                "platnost": f"do {i}. 4. 2026",
            }
            for i in range(100)
        ]
        akce_cog.scraper.scrape.return_value = mock_results

        await akce_cog._send_discounts(
            interaction=mock_interaction,
            title="Test Product",
            empty_text="No discounts found.",
            error_text="Error occurred",
            url="https://example.com",
            emoji="🔥",
        )

        mock_interaction.response.send_message.assert_called_once()
        assert mock_interaction.followup.send.call_count >= 1

    @pytest.mark.asyncio
    async def test_correct_parameters(self, akce_cog, mock_interaction):
        """All parameters used correctly."""
        mock_results = [
            {
                "nazev": "Shop",
                "cena": "50 Kc",
                "sleva": "-10%",
                "platnost": "dnes",
            }
        ]
        akce_cog.scraper.scrape.return_value = mock_results

        await akce_cog._send_discounts(
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
        assert "50 Kc" in call_args
