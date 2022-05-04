import json

from apscheduler.schedulers.background import BackgroundScheduler
from forta_agent import FindingSeverity, FindingType, Finding, get_transaction_receipt

from .forecast import get_today_forecast as get_today_forecast_function
from .forecast import update_optimal_parameters_for_pool as update_optimal_parameters_for_pool_function
from .parser import get_protocol_last_day_data as get_protocol_last_day_data_function
from .parser import update_pools_data as update_pools_data_function

findings_count = 0  # the number of findings
config = []  # in-memory config data
forecast_prices = {}  # map pool -> today's forecasted price


def initialize():
    """
    Runs when the agent starts. It runs routines and adds the job to the scheduler in order to
    update data for forecasting.
    :return:
    """
    parse_config()
    update_pools_data_function()
    update_forecast_prices()
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_pools_data_function, 'interval', hours=24)
    scheduler.add_job(parse_config, 'interval', hours=24)
    scheduler.add_job(update_forecast_prices, 'interval', hours=24)
    scheduler.add_job(update_optimal_parameters_for_pool_function, 'interval', days=28)
    scheduler.start()


def parse_config():
    """
    Parses config and update in-memory variable in run-time
    """
    global config
    config = []
    with open('./config.json', 'r') as f:
        config_json = json.load(f)
        for protocol in config_json['protocols']:
            pools = []
            for pool in config_json['protocols'][protocol]['pools']:
                pools.append(pool)
            p = {protocol: pools}
            config.append(p)


def update_forecast_prices():
    """
    Update today's forecast price
    """
    global forecast_prices, config
    for protocol in config:
        for key, value in protocol.items():
            for pool in value:
                trend, yearly_upper, yhat = get_today_forecast_function(pool)
                forecast_prices[pool] = {"trend": trend, "yearly_upper": yearly_upper, "yhat": yhat}


def create_finding(severity, price_change, pool):
    """
    Creates a new finding with given severity, price change and pool
    :rtype: Finding
    """
    return Finding({
        'name': 'Unusual Price Change',
        'description': f'Unusual Price Change: {price_change}',
        'alert_id': 'FORTA-777',
        'type': FindingType.Suspicious,
        'severity': severity,
        'metadata': {
            'price_change': price_change,
            'pool': pool
        }
    })


def provide_handle_transaction(get_transaction_receipt):
    def handle_transaction(transaction_event):
        global findings_count, forecast_prices
        # limiting this agent to emit only 5 findings so that the alert feed is not spammed
        if findings_count >= 5:
            return []

        findings = []

        for protocol in config:
            for key, value in protocol.items():
                for pool in value:
                    # if a pool in transaction addresses set, make a comparison to determine if there is an unusual
                    # price change
                    if pool in transaction_event.addresses:
                        last_price = get_protocol_last_day_data_function(key, pool)
                        print(forecast_prices[pool]['trend'])
                        difference = forecast_prices[pool]['trend'] - float(last_price)
                        if abs(difference) >= forecast_prices[pool]['yearly_upper']:
                            finding = create_finding(FindingSeverity.Critical, abs(difference), pool)
                            findings.append(finding)
                            findings_count += len(findings)
                        elif abs(difference) >= forecast_prices[pool]['yearly_upper'] / 2:
                            finding = create_finding(FindingSeverity.High, abs(difference), pool)
                            findings.append(finding)
                            findings_count += len(findings)
        return findings

    return handle_transaction


real_handle_transaction = provide_handle_transaction(get_transaction_receipt)


#  Forta SDK listener
def handle_transaction(transaction_event):
    return real_handle_transaction(transaction_event)
