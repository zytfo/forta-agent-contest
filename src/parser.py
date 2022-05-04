import csv
import json
import os
from datetime import datetime
import time

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Start timestamp to fetch data from
START_TIMESTAMP = 1620086400

# In-memory variable to check if there is a support for a protocol
AVAILABLE_PROTOCOLS = ["uniswap-v3"]


def build_client(url):
    """
    Protocol client to make requests to sub-graph
    :param url: protocol url
    """
    return Client(
        transport=RequestsHTTPTransport(
            url=url,
            verify=True,
            retries=3
        )
    )


def get_datetime(timestamp):
    """
    Convert UNIX timestamp ot human-readable date
    :param timestamp: UNIX timestamp
    """
    return datetime.fromtimestamp(timestamp)


def get_uniswap_data(pool, timestamp, client):
    """
    Fetch data from Uniswap protocol and store it in pools data folder
    :param pool: pool to fetch data
    :param timestamp: UNIX timestamp to get data from
    :param client: client to send request from
    """
    query = gql('''
        {
          poolDayDatas(first: 1000, orderBy: date, where: {
            pool: "''' + str(pool) + '''",
            date_gt: ''' + str(timestamp) + '''
          } ) {
            date
            token0Price
            token1Price
          }
        }''')
    with open('./pools_data/' + pool + '.csv', 'w') as d:
        header = ['date', 'price']
        writer = csv.writer(d)
        writer.writerow(header)
        data = client.execute(query)
        for i in data['poolDayDatas']:
            row = [datetime.fromtimestamp(i['date']), i['token0Price']]
            writer.writerow(row)
        d.flush()
        os.fsync(d.fileno())


def get_uniswap_last_day_data(pool, timestamp, client):
    """
    Get last day data from Uniswap pool
    :param pool: a pool to get historical data from
    :param timestamp: UNIX timestamp
    :param client: client to send request from
    """
    query = gql('''
        {
          poolDayDatas(first: 1, orderBy: date, where: {
            pool: "''' + str(pool) + '''",
            date_gt: ''' + str(timestamp) + '''
          } ) {
            date
            token0Price
            token1Price
          }
        }''')
    data = client.execute(query)
    return data['poolDayDatas'][0]['token0Price']


def get_protocol_data(protocol, pool, timestamp, client):
    """
    Matches protocol and the way of getting data
    """
    if protocol == 'uniswap-v3':
        get_uniswap_data(pool, timestamp, client)


def get_protocol_last_day_data(protocol, pool):
    """
    Universal last data retriever. Calls appropriate function based on the protocol
    :param protocol: protocol to get data from
    :param pool: a pool to get data from
    """
    if protocol == 'uniswap-v3':
        client = build_client("https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3")
        ts = int(time.time()) - (60 * 60 * 24)
        return get_uniswap_last_day_data(pool, ts, client)


def update_pools_data():
    """
    Updates pools data based on the configuration
    """
    with open('config.json', 'r') as f:
        config = json.load(f)
        for protocol in config['protocols']:
            if protocol in AVAILABLE_PROTOCOLS:
                client = build_client(config['protocols'][protocol]['subgraph-url'])
                for pool in config['protocols'][protocol]['pools']:
                    get_protocol_data(protocol, pool, START_TIMESTAMP, client)
