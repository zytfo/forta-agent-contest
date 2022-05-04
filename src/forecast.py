import json
import logging
import os
import sys
import warnings
from datetime import date

import optuna
import pandas as pd
from fbprophet import Prophet
from sklearn.metrics import mean_absolute_error

# ignore warnings so Forta SDK will not crash
warnings.filterwarnings("ignore")

logging.getLogger('fbprophet').setLevel(logging.WARNING)
logging.disable(sys.maxsize)

# default pre-trained params in case there are no optimal parameters for a pool
DEFAULT_PARAMS = {
    'changepoint_prior_scale': 0.45630165790829486,
    'changepoint_range': 0.16656098641709344,
    'seasonality_mode': 'additive',
    'seasonality_prior_scale': 9.144413372447056,
    'yearly_seasonality': 5,
    'holidays_prior_scale': 6.520734116879363
}

# global variables to find optimal params using Optuna
train_temp_df = pd.DataFrame()
validation_temp_df = pd.DataFrame()


def find_params(trial):
    """
    Optuna sub-routine to find optimal params for a model
    :param trial: number of trials
    :return: mae for a current trial
    """
    # Set of all possible hyperparameters
    parameters = {
        'changepoint_prior_scale': trial.suggest_float('changepoint_prior_scale', 0.005, 5),
        'changepoint_range': trial.suggest_float('changepoint_range', 0.1, 0.9),
        'seasonality_mode': trial.suggest_categorical('seasonality_mode', ['multiplicative', 'additive']),
        'seasonality_prior_scale': trial.suggest_float('seasonality_prior_scale', 0.1, 10),
        'yearly_seasonality': trial.suggest_int('yearly_seasonality', 1, 50),
        'holidays_prior_scale': trial.suggest_float('holidays_prior_scale', 0.1, 10)
    }
    # Model initialization
    m = Prophet(**parameters,
                interval_width=0.95,
                weekly_seasonality=False,
                daily_seasonality=False
                )
    # Disabling Prophet logs
    with suppress_stdout_stderr():
        m.fit(train_temp_df)
        validation = m.predict(validation_temp_df)
    # Calculation of MAE
    mae_for_optuna = mean_absolute_error(validation_temp_df['y'], validation['yhat'])
    return mae_for_optuna


def preprocess_dataframe(df):
    """
    Pre-process dataframe to parse date column correctly
    :param df: dataframe to process
    """
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').resample('D').mean().reset_index()
    df.columns = ["ds", "y"]
    return df


def get_train_dataframe(df):
    """
    Split dataframe into train and validation sets
    :param df: dataframe to split
    """
    test_len_tun = int(df.shape[0] / 10)
    train_df_tun = df.iloc[:-test_len_tun, :]
    val_df_tun = df.iloc[-test_len_tun:int(-test_len_tun / 2), :]
    train_df_tun2 = pd.concat([train_df_tun, val_df_tun])
    return train_df_tun2, val_df_tun


def get_today_forecast(pool):
    """
    Get forecast for a pool to get today's price to compare later
    :param pool: make forecast for a desired pool
    """
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
    with suppress_stdout_stderr():
        model.fit(train_df)
        future_optuna_df = model.make_future_dataframe(periods=60, freq='D')
        forecast = model.predict(future_optuna_df)
    mask = (forecast['ds'].dt.date == date.today())
    return float(forecast[mask]['trend'].values[0]), float(forecast[mask]['yearly_upper'].values[0]), float(
        forecast[mask]['yhat'].values[0])


def update_optimal_parameters_for_pool():
    """
    Subroutine which searches for the best parameters
    """
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


# Custom class to hide Prophet logs (there is no other way :D)
class suppress_stdout_stderr(object):
    """
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).
    """

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        for fd in self.null_fds + self.save_fds:
            os.close(fd)
