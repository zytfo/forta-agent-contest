from unittest.mock import Mock
from forta_agent import FindingType, create_transaction_event
from .agent import provide_handle_transaction, parse_config, update_pools_data_function, update_forecast_prices

mock_get_transaction_receipt = Mock()
handle_transaction = provide_handle_transaction(mock_get_transaction_receipt)


class TestUnusualPriceChangeAgent:
    # may fail in case of changed forecasted price
    def test_returns_finding_for_uni_eth_pool(self):
        parse_config()
        update_pools_data_function()
        update_forecast_prices()
        tx_event = create_transaction_event({"addresses": ["0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801"]})

        findings = handle_transaction(tx_event)
        assert len(findings) == 1
        assert findings[0].severity == FindingType.Suspicious

    def test_returns_no_finding_for_incorrect_pool(self):
        parse_config()
        update_pools_data_function()
        update_forecast_prices()
        tx_event = create_transaction_event({"addresses": ["0x1d42064fc4beb5f8aaf85f4617ae8b3b5b877777"]})

        findings = handle_transaction(tx_event)
        assert len(findings) == 0

    def test_returns_no_finding_without_parsing_config(self):
        update_pools_data_function()
        update_forecast_prices()
        tx_event = create_transaction_event({"addresses": ["0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801"]})

        findings = handle_transaction(tx_event)
        assert len(findings) == 0

    def test_returns_no_finding_without_updating_prices(self):
        update_pools_data_function()
        tx_event = create_transaction_event({"addresses": ["0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801"]})

        findings = handle_transaction(tx_event)
        assert len(findings) == 0
