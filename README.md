# [Forta Contest 2](https://docs.forta.network/en/latest/contest6-forta/): Unusual Price Changes Monitor Agent

## Description

This agent detects transactions with unusual price changes from different protocols and pools using [Facebook Prophet](https://facebook.github.io/prophet/) time-series anomaly detection and Optuna for finding the best parameters based on various options such as seasonality, holidays, etc.

Check out data science flow in [Jupyter Notebook](https://github.com/zytfo/forta-unusual-price-change-agent/blob/main/anomaly-detection.ipynb). 

## Supported Chains

- Ethereum

## Supported Protocols

- Uniswap-V3

## Alerts

- FORTA-99
  - Fired when a price change is more than the absolute difference between an actual price and forecasted price (trend) + possible upper bound
  - Type is always set to "suspicious"
  - Metadata "price_change" field contains the price difference between forecasted and actual prices
  - Metadata "pool" field contains the pool address
  - Metadata "last_actual_price" contains the last actual price fetched from the protocol
  - Metadata "forecasted_upper" contains forecasted upper threshold
  - Metadata "forecasted_upper_bound" contains forecasted_price + forecasted_upper
  - Metadata "forecasted_lower_bound" contains forecasted_price - forecasted_upper

## Test Data
Test data provided for a UNI/WETH pool: `0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801`.
One of the tests may fail due to the non-deterministic nature of the project. 

## Running Locally
1. Run `npm install` to install the required packages
2. Run `npm test` to run the unit tests
3. Run `npm start` to start the agent locally

## Attention!
When adding a new pool it is required to run `update_optimal_parameters_for_pool` method manually or wait for 28 days when new optimal parameters will be found. It was done for simplicity and to avoid time-consuming training during the start of the agent. By default, it uses default optimal parameters for training data. You can add optimal parameters either used the method or add them to the `optimal_params` folder with `pool_address.json` name. 

---
## Implementation
This section contains the implementation details of the Forta agent.

### Historical Data Fetching and Preparation: [parser.py](https://github.com/zytfo/forta-unusual-price-change-agent/blob/main/src/parser.py)
In order to train the model, it was necessary to collect historical data on desired pools. At the moment, the processing of prices from the **Uniswap-V3** protocol has been implemented using their [subgraph](https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3). It is possible to add and remove protocols and pools in the **RUNTIME** using `config.json`:
```
{
  "protocols": {
    "uniswap-v3": {
      "subgraph-url": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
      "pools": [
        "0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801",
        "0xac4b3dacb91461209ae9d41ec517c2b9cb1b7daf",
        "0xe05e653453f733786f2dabae0ffa1e96cfcc4b25",
        "0xf56d08221b5942c428acc5de8f78489a97fc5599"
      ]
    }
  }
}
```
The next update of protocols and pools will be done `24 hours` after the start of the agent (configurable).
The `parser.py` fetches data using protocol url and pools addresses from the `config.json` and stores all available historical pools data in the `pools_data` folder. Pools data update happens when the agent starts and happens every `24 hours` (configurable, doesn't make sense make oftener). The pool data has the following format (e.g. `0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801.csv`):
```
date,price
2021-05-05 02:00:00,83.58054735312220946857158160353627
2021-05-06 02:00:00,87.04714792556642458890951794960397
2021-05-07 02:00:00,87.62208772640826217639477753941856
2021-05-08 02:00:00,96.01659003383089028154459772839863
...
```

### Data Science: [forecast.py](https://github.com/zytfo/forta-unusual-price-change-agent/blob/main/src/forecast.py)
##### Check out all the flow in my [Jupyter Notebook](https://github.com/zytfo/forta-unusual-price-change-agent/blob/main/anomaly-detection.ipynb).
After pools data loading, it is time for some Data Science. In order to get trend information and make some forecasts for a pair, [Facebook Prophet](https://facebook.github.io/prophet/) and [Optuna](https://optuna.readthedocs.io/en/stable/faq.html) have been used.
To find optimal parameters for a Prophet model, an Optuna job has been initiated. It runs `100` trials (actually, not so many, but more trials takes more time) for each pool in order to get best parameters to train a model. Parameters from which the sample is made:
```
parameters = {
        'changepoint_prior_scale': trial.suggest_float('changepoint_prior_scale', 0.005, 5),
        'changepoint_range': trial.suggest_float('changepoint_range', 0.1, 0.9),
        'seasonality_mode': trial.suggest_categorical('seasonality_mode', ['multiplicative', 'additive']),
        'seasonality_prior_scale': trial.suggest_float('seasonality_prior_scale', 0.1, 10),
        'yearly_seasonality': trial.suggest_int('yearly_seasonality', 1, 50),
        'holidays_prior_scale': trial.suggest_float('holidays_prior_scale', 0.1, 10)
    }
```
Best parameters are forced to recalculate every `28 days` (configurable) after the start of the agent and store the best options inside the `optimal_params` folder for every pool.
So, for instance, pool `0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801` has the following best options after `100` trials (based on minimization of **MAE**):
```
{
    "changepoint_prior_scale": 0.45630165790829486, 
    "changepoint_range": 0.16656098641709344, 
    "seasonality_mode": "additive", 
    "seasonality_prior_scale": 9.144413372447056, 
    "yearly_seasonality": 5, 
    "holidays_prior_scale": 6.520734116879363
}
```
When the best parameters are found, the **fit**/**predict** routine starts. It evaluates the corresponding pool data and makes a forecast for the next `60 days`. For instance, a trend forecast for the `0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801` pool:

![Chart](https://github.com/zytfo/forta-unusual-price-change-agent/blob/main/blob/chart.png?raw=true)

Using this data it is possible to identify if the current price is in the trend or not and say if it is an **anomaly**. The current day forecasted price is stored in memory, so only need to compare a new price from the protocol.

### Forta Agent: : [agent.py](https://github.com/zytfo/forta-unusual-price-change-agent/blob/main/src/agent.py)
When the Forta agent starts, it makes some initialization:
- `parse_config()`: stores all information about protocols and pools in memory
- `update_pools_data_function()`: update historical price data for each pool and stores in the `pools_data` folder
- `update_forecast_prices()`: retrain a Prophet model based on the updated pool data
- `add scheduler` with the following routins:
    * `update_pools_data_function()` every `24 hours`
    * `parse_config()` every `24 hours`
    * `update_forecast_prices()` every `24 hours`
    * `update_optimal_parameters_for_pool_function()` every `28 days`

After that, it starts listening for a `transaction_event` and checks if there is a match of addresses in the available pools and transactions. If matches, it gets the current day forecasted price, makes a request to get the current price using the protocol's subgraph and analyses if this new price is in the forecasted trend or not. 

Then it creates a new `Finding` and fires it in case of `Critical` (if the price change is more than the forecasted `forecasted_upper` threshold) or `High` (if the price change is more than half of the forecasted `forecasted_upper` threshold) severities.

```
Finding = {
  name: Unusual Price Change,
  description: Unusual Price Change: {price_change} for Pool: {pool},
  alert_id: FORTA-99,
  type: FindingType.Suspicious,
  severity: severity,
  metadata: {
    price change: the difference between forecasted price and actual price,
    pool: pool address,
    last_actual_price: last actual price gotten from protocol,
    forecasted_upper: forecasted upper threshold,
    forecasted_upper_bound: forecasted_price + forecasted_upper,
    forecasted_lower_bound: forecasted_price - forecasted_upper
  }
}
```

### Example
```
APE/WETH pool:
forecasted price on 04/05/2022: 186.3898830915793178870644949177326
forecasted upper bound on 04/05/2022: 187.1234323123543238659343434654321
forecasted upper on 04/05/2022: 0.733549221
actual price: 184
difference b/w forecasted price and actual price: 
  186.3898830915793178870644949177326 - 184 = 2.38988309 > 0.733549221 -> FIRE!!! (in this case critical)
```