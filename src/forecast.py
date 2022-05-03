import json
import os
from datetime import date

import optuna
import pandas as pd
from fbprophet import Prophet
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error

DEFAULT_PARAMS = {
    'changepoint_prior_scale': 0.45630165790829486,
    'changepoint_range': 0.16656098641709344,
    'seasonality_mode': 'additive',
    'seasonality_prior_scale': 9.144413372447056,
    'yearly_seasonality': 5,
    'holidays_prior_scale': 6.520734116879363
}

train_temp_df = pd.DataFrame()
validation_temp_df = pd.DataFrame()


def evaluate(y_true, y_pred):
    return {
        'MAE': mean_absolute_error(y_true, y_pred),
        'MSE': mean_squared_error(y_true, y_pred)
    }


def find_params(trial):
    parameters = {
        'changepoint_prior_scale': trial.suggest_float('changepoint_prior_scale', 0.005, 5),
        'changepoint_range': trial.suggest_float('changepoint_range', 0.1, 0.9),
        'seasonality_mode': trial.suggest_categorical('seasonality_mode', ['multiplicative', 'additive']),
        'seasonality_prior_scale': trial.suggest_float('seasonality_prior_scale', 0.1, 10),
        'yearly_seasonality': trial.suggest_int('yearly_seasonality', 1, 50),
        'holidays_prior_scale': trial.suggest_float('holidays_prior_scale', 0.1, 10)
    }
    m = Prophet(**parameters,
                interval_width=0.95,
                weekly_seasonality=False,
                daily_seasonality=False
                )
    m.fit(train_temp_df)
    validation = m.predict(validation_temp_df)
    mae_for_optuna = mean_absolute_error(validation_temp_df['y'], validation['yhat'])
    return mae_for_optuna


def preprocess_dataframe(df):
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').resample('D').mean().reset_index()
    df.columns = ["ds", "y"]
    return df


def get_train_dataframe(df):
    test_len_tun = int(df.shape[0] / 10)
    train_df_tun = df.iloc[:-test_len_tun, :]
    val_df_tun = df.iloc[-test_len_tun:int(-test_len_tun / 2), :]
    train_df_tun2 = pd.concat([train_df_tun, val_df_tun])
    return train_df_tun2, val_df_tun


def get_today_forecast(pool, number_of_days):
    df = pd.read_csv('./pools_data/' + pool + '.csv')
    df = preprocess_dataframe(df)
    train_df, val_df_tun = get_train_dataframe(df)
    optimal_params = DEFAULT_PARAMS
    try:
        with open('./optimal_params/' + pool + '.json', 'r') as json_file:
            optimal_params = json.load(json_file)
    except Exception:
        pass
    model = Prophet(**optimal_params,
                    interval_width=0.95,
                    weekly_seasonality=False,
                    daily_seasonality=False
                    )
    model.fit(train_df)
    future_optuna_df = model.make_future_dataframe(periods=number_of_days, freq='D')
    forecast = model.predict(future_optuna_df)
    mask = (forecast['ds'].dt.date == date.today())
    return forecast[mask]


def get_optimal_parameters_for_pool():
    with open('config.json', 'r') as f:
        config = json.load(f)
        for protocol in config['protocols']:
            for pool in config['protocols'][protocol]['pools']:
                df = pd.read_csv('./pools_data/' + pool + '.csv')
                df.columns = ["ds", "y"]
                global train_temp_df, validation_temp_df
                train_temp_df, validation_temp_df = get_train_dataframe(df)
                study = optuna.create_study(direction='minimize')
                study.optimize(find_params, n_trials=100)
                best_params = study.best_params
                with open('./optimal_params/' + pool + '.json', 'w') as outfile:
                    json.dump(best_params, outfile)
                    outfile.flush()
                    os.fsync(outfile.fileno())
