import optuna
import pandas as pd
from fbprophet import Prophet
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error

OPTIMAL_PARAMS = {
    'changepoint_prior_scale': 0.45630165790829486,
    'changepoint_range': 0.16656098641709344,
    'seasonality_mode': 'additive',
    'seasonality_prior_scale': 9.144413372447056,
    'yearly_seasonality': 5,
    'holidays_prior_scale': 6.520734116879363
}


def evaluate(y_true, y_pred):
    return {
        'MAE': mean_absolute_error(y_true, y_pred),
        'MSE': mean_squared_error(y_true, y_pred)
    }


def find_params(trial, train_df_tun, val_df_tun):
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
    m.fit(train_df_tun)
    validation = m.predict(val_df_tun)
    mae_for_optuna = mean_absolute_error(val_df_tun['y'], validation['yhat'])
    return mae_for_optuna


def get_optimal_params():
    study = optuna.create_study(direction='minimize')
    study.optimize(find_params, n_trials=1000)
    return study.best_params


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
    return train_df_tun2


def get_forecast(pool, number_of_days):
    df = pd.read_csv('./pools_data/' + pool + '.csv')
    df = preprocess_dataframe(df)
    train_df = get_train_dataframe(df)
    model = Prophet(**OPTIMAL_PARAMS,
                    interval_width=0.95,
                    weekly_seasonality=False,
                    daily_seasonality=False
                    )
    model.fit(train_df)
    future_optuna_df = model.make_future_dataframe(periods=number_of_days, freq='D')
    forecast = model.predict(future_optuna_df)
    forecast_final = forecast[['ds', 'trend', 'yhat']]
    return forecast_final
