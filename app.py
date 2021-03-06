import yfinance as yf
import streamlit as st
import datetime 
import numpy as np
#import matplotlib.ticker as mticker
import pandas as pd
import requests
import sklearn.metrics as metrics
# multivariate output stacked lstm example
from numpy import array
from numpy import hstack
import tensorflow as tf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt
import mpl_finance as mpf 
from sklearn.preprocessing import MinMaxScaler
import mplcursors
import plotly.graph_objects as go
from tensorflow.keras import backend as K
from keras.models import load_model
from keras.layers import Input
from keras.layers import Dropout
from keras.layers import Activation
from keras.layers import Bidirectional
from keras.layers import TimeDistributed,Conv1D,MaxPooling1D,Flatten
from keras.callbacks import EarlyStopping
from keras.callbacks import ModelCheckpoint
from keras.constraints import maxnorm
from keras.models import Sequential
from keras.layers import LSTM,Embedding
from keras.layers import Dense
from keras.optimizers import Adam,SGD

class attention(tf.keras.layers.Layer):
    
    def __init__(self, return_sequences=True):
        self.return_sequences = return_sequences
        super(attention,self).__init__()
        
    def build(self, input_shape):
        
        self.W=self.add_weight(name="att_weight", shape=(input_shape[-1],1),
                               initializer="normal")
        self.b=self.add_weight(name="att_bias", shape=(input_shape[1],1),
                               initializer="zeros")
        
        super(attention,self).build(input_shape)
        
    def call(self, x):
        
        e = K.tanh(K.dot(x,self.W)+self.b)
        a = K.softmax(e, axis=1)
        output = x*a
        
        if self.return_sequences:
            return output
        
        return K.sum(output, axis=1)

def customLoss(ytrue,ypred):  
    diff = ypred - ytrue
    upperband = K.less(tf.cast(ytrue, dtype=tf.float32, name=None),tf.constant(0.6))
    
    upperband = K.cast(upperband, K.floatx()) #1 for lower, 0 for greater
    # print(upper
    p_upperband = K.less(tf.cast(ypred, dtype=tf.float32, name=None),tf.constant(0.6))
    
    p_upperband = K.cast(p_upperband, K.floatx()) #1 for lower, 0 for greater
    lowerband = K.greater(tf.cast(ytrue, dtype=tf.float32, name=None),tf.constant(0.2))
    lowerband = K.cast(lowerband, K.floatx()) #0 for lower, 1 for greater
    
    p_lowerband = K.greater(tf.cast(ypred, dtype=tf.float32, name=None),tf.constant(0.2))
    p_lowerband = K.cast(p_lowerband, K.floatx()) #0 for lower, 1 for greater

    ub_check = K.not_equal(upperband,p_upperband)
    ub_check = K.cast(ub_check, K.floatx())
    ub_check = ub_check + 1
    lb_check = K.not_equal(lowerband,p_lowerband)
    lb_check = K.cast(lb_check, K.floatx())
    lb_check = lb_check + 1
    band = K.equal(upperband,lowerband)
    band = K.cast(band, K.floatx())
    band = band + 1                 #1 for lower, 2 for greater
    greater = K.greater(tf.abs(diff),tf.constant(0.3))
    greater = K.cast(greater, K.floatx()) #0 for lower, 1 for greater
    greater = greater + 1                 #1 for lower, 2 for greater

    #use some kind of loss here, such as mse or mae, or pick one from keras
    #using mse:
    return (ub_check * lb_check * band * greater * K.square(diff))

yf.pdr_override()

lookback_days=30
forward_days =3


model = Sequential()
model.add((Conv1D(filters=32, kernel_size=5, activation='relu',
                                 input_shape=(30,7))))
model.add((MaxPooling1D(pool_size=2)))
model.add(Bidirectional(LSTM(100, return_sequences=True,
              activation='tanh', recurrent_activation='hard_sigmoid',kernel_initializer='random_uniform')))
model.add(Dropout(0.5))
model.add(Bidirectional(LSTM(100, return_sequences=True,
              activation='relu', recurrent_activation='hard_sigmoid',kernel_initializer='random_uniform')))
model.add(Dropout(0.5))
model.add(attention(return_sequences=False))
model.add((Dense(6)))
opt = Adam(lr=0.001)
model = tf.keras.models.load_model('Models/Actual_model', custom_objects={'customLoss':customLoss})
es = tf.keras.callbacks.EarlyStopping(monitor='val_loss', mode='min',  patience=30)
model.compile(optimizer=opt, loss='mse', metrics=['mse','mae','mape'])
model.save('my_model')
st.write("""
# Stock Prediction Web Application
""")


st.sidebar.header('User Input Parameters')

def rsquared(y, y_hat):
    y_bar = y.mean()
    ss_tot = ((y-y_bar)**2).sum()
    ss_res = ((y-y_hat)**2).sum()
    return 1 - (ss_res/ss_tot)

def get_technical_indicators(dataset):
    # Create 7 and 30 days Moving Average
    dataset['ma7'] = dataset['Close'].rolling(window=7, min_periods = 1).mean()
    dataset['ma26'] = dataset['Close'].rolling(window=26, min_periods = 1).mean()

    dataset['ma7_open'] = dataset['Open'].rolling(window=7, min_periods = 1).mean()
    dataset['ma26_open'] = dataset['Open'].rolling(window=26, min_periods = 1).mean()
    
    
    # Create MACD
    dataset['26ema'] = dataset['Close'].ewm(span=26).mean()
    dataset['12ema'] = dataset['Close'].ewm(span=12).mean()
    dataset['MACD'] = (dataset['12ema']-dataset['26ema'])
    # Create Bollinger Bands
    dataset['20sd'] = dataset['Close'].rolling(window=20, min_periods = 1).std()
    dataset['20sd'] = dataset['20sd'].fillna(method='backfill').dropna()
    dataset['upper_band'] = dataset['ma26'] + (dataset['20sd']*2)
    dataset['lower_band'] = dataset['ma26'] - (dataset['20sd']*2)

    dataset['Close_lag1'] = dataset['Close'] .shift(1)
    #dataset['Close_lag1'] = dataset['Close_lag1'].fillna(method='backfill').dropna()
    dataset['Close_lag2'] = dataset['Close'] .shift(2)
    #dataset['Close_lag2'] = dataset['Close_lag2'].fillna(method='backfill').dropna()
    dataset['Close_lag3'] = dataset['Close'] .shift(3)
    #dataset['Close_lag3'] = dataset['Close_lag3'].fillna(method='backfill').dropna()
    dataset['Close_lag4'] = dataset['Close'] .shift(4)
    #dataset['Close_lag4'] = dataset['Close_lag4'].fillna(method='backfill').dropna()
    dataset['Close_lag5'] = dataset['Close'] .shift(5)
    #dataset['Close_lag5'] = dataset['Close_lag5'].fillna(method='backfill').dropna()
    
    # Create Exponential moving average
    dataset['ema'] = dataset['Close'].ewm(com=0.5).mean()
    
    # Create Momentum
    #dataset['momentum'] = dataset['Close']-1
    
    return dataset

def split_sequences(sequences, sequences_y,  n_steps_in, n_steps_out):
	X, y = list(), list()
	for i in range(len(sequences)):
		# find the end of this pattern
		end_ix = i + n_steps_in
		out_end_ix = end_ix + n_steps_out
		# check if we are beyond the dataset
		if out_end_ix > len(sequences):
			break
		# gather input and output parts of the pattern
		seq_x, seq_y = sequences[i:end_ix, :], sequences_y[end_ix:out_end_ix, :]
		X.append(seq_x)
		y.append(seq_y)
	return array(X), array(y)

def test_data_prediction(df_test):
  #df_test['Date'] = pd.to_datetime(df_test['Date'])
  #df_test.set_index('Date', inplace=True)



  df_test_ti = get_technical_indicators(df_test)
  #df_test_ti = df_test_ti.dropna()
  df_test = df_test.fillna(method='backfill')
  df_test_y = df_test.copy()
  df_test_y = df_test_y[['Open','Close']]
  df_test_ti = df_test_ti[['Open','Close','High', 'Low','Volume','20sd','MACD']]

  args_test = df_test_ti.values.reshape(df_test_ti.shape[0],7)
  args_test_y = df_test_y.values.reshape(df_test_y.shape[0],2)

  in_seq_test = args_test
  in_seq_test_y = args_test_y

  division =  lookback_days

  data_train = in_seq_test[:division]
  data_test = in_seq_test[(division-lookback_days):]

  data_train_y = in_seq_test_y[:division]
  data_test_y = in_seq_test_y[(division-lookback_days):]

  X_test, y_test = split_sequences(data_test, data_test_y, lookback_days,forward_days)

  X_features = X_test.shape[2]
  y_features = y_test.shape[2]
  X_test_original = X_test
  X_test=X_test.reshape(X_test.shape[0],lookback_days*X_features)
  y_test=y_test.reshape(y_test.shape[0],forward_days*y_features)

  xtest_scaler = MinMaxScaler().fit(X_test)
  X_test = xtest_scaler.transform(X_test)
  ytest_scaler = MinMaxScaler().fit(y_test)
  #y_scaler.fit(y_test)
  y_test = ytest_scaler.transform(y_test)

  X_test = X_test.reshape(X_test.shape[0],lookback_days, X_features)

  y_pred = model.predict(X_test,batch_size = 16)
  y_pred = y_pred.reshape(y_pred.shape[0],forward_days*y_features)
  y_hat = ytest_scaler.inverse_transform(y_pred)

  y_test = y_test.reshape(y_test.shape[0],forward_days*y_features)
  #y_true = y_test
  y_true = ytest_scaler.inverse_transform(y_test)

  return y_test,y_true,y_pred,y_hat,X_test_original

today = datetime.date.today()
def user_input_features():
    ticker = st.sidebar.text_input("Ticker", 'GOOG')
    start_date = st.sidebar.text_input("Start Date", '2020-06-01')
    end_date = st.sidebar.text_input("End Date", '2020-12-30' ) #f'{today}')
    return ticker, start_date, end_date

symbol, start, end = user_input_features()

def get_symbol(symbol):
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(symbol)
    result = requests.get(url).json()
    for x in result['ResultSet']['Result']:
        if x['symbol'] == symbol:
            return x['name']
company_name = get_symbol(symbol.upper())


start = pd.to_datetime(start)
end = pd.to_datetime(end)

# Read data 
data = yf.download(symbol,start,end)

y_test1,y_true1,y_pred1,y_hat1, X_test_original1 = test_data_prediction(data)

y_test=y_test1
y_true=y_true1
y_pred=y_pred1
y_hat=y_hat1
X_test_original = X_test_original1

diff_true = array([y_true[:,x] - X_test_original[:,1,-1] for x in [0,1,2,3,4,5]])
diff_pred = array([y_hat[:,x] - X_test_original[:,0,-1] for x in [0,1,2,3,4,5]])

diff_true1 = array([y_true[:,x] - X_test_original[:,1,-1] for x in [1,3,5]])
diff_true2 = array([y_true[:,x] - X_test_original[:,0,-1] for x in [0,2,4]])
diff_true=np.concatenate((diff_true1,diff_true2),axis=1)

diff_pred1 = array([y_hat[:,x] - X_test_original[:,1,-1] for x in [1,3,5]])
diff_pred2 = array([y_hat[:,x] - X_test_original[:,0,-1] for x in [0,2,4]])
diff_pred=np.concatenate((diff_pred1,diff_pred2),axis=1)

import sklearn.metrics as metrics
mae = metrics.mean_absolute_error(y_true, y_hat)
mse = metrics.mean_squared_error(y_true, y_hat)
rmse = np.sqrt(mse) #mse**(0.5)  
r2 = rsquared(y_true, y_hat)
mae_diff = metrics.mean_absolute_error(diff_true, diff_pred)
mse_diff = metrics.mean_squared_error(diff_true, diff_pred)
rmse_diff = np.sqrt(mse_diff) #mse**(0.5)  
r2_diff = rsquared(diff_true, diff_pred)
print("Results of sklearn.metrics:")
print("MAE:",mae)
print("MSE:", mse)
print("RMSE:", rmse)
print("R-Squared:", r2)
print("MAE_diff:",mae_diff)
print("MSE_diff:", mse_diff)
print("RMSE_diff:", rmse_diff)
print("R-Squared diff:", r2_diff)

st.write("MAE : " , mae)
st.write("MSE : " , mse)
st.write("RMSE : " , rmse)
st.write("R-Squared : " , r2)

y_bar = y_true.mean()
ss_tot = ((y_true-y_bar)**2).sum()
ss_res = ((y_true-y_hat)**2).sum()
print(ss_res)
print(ss_tot)

y_bar = diff_true.mean()
ss_tot = ((diff_true-y_bar)**2).sum()
ss_res = ((diff_true-diff_pred)**2).sum()
print(ss_res)
print(ss_tot)
print(ss_res/ss_tot)

y_pred=y_hat
y_pred_len = y_pred.shape[0]

new_row1 = {'open':y_pred[-2,2] , 'close':y_pred[-2,3]}
new_row2 = {'open':y_pred[-1,4] , 'close':y_pred[-1,4]}

from datetime import timedelta

dataset = pd.DataFrame({
    'open': y_pred[:,0], 'close': y_pred[:,1]
                        })

dataset_true = pd.DataFrame({
    'open': y_true[:,0], 'close': y_true[:,1]
                        })

tempDf = pd.to_datetime(data[-y_pred_len-2:-2].index)
dataset.loc[:,'date'] = pd.to_datetime(data[-y_pred_len-2:-2].index)
dataset_true.loc[:,'date'] = pd.to_datetime(data[-y_pred_len-2:-2].index)

dataset = dataset.append(new_row1, ignore_index=True)
dataset = dataset.append(new_row2, ignore_index=True)
dataset.loc[y_pred_len,'date'] = pd.to_datetime(tempDf[-1] + timedelta(days=1))
dataset.loc[y_pred_len+1,'date'] = pd.to_datetime(tempDf[-1] + timedelta(days=2))

dataset=dataset.assign(low=lambda d: d[['open', 'close']].min(1))
dataset=dataset.assign(high=lambda d: d[['open', 'close']].max(1))
dataset_true=dataset_true.assign(low=lambda d: d[['open', 'close']].min(1))
dataset_true=dataset_true.assign(high=lambda d: d[['open', 'close']].max(1))

import plotly.graph_objects as go

import pandas as pd
from datetime import datetime

fig = go.Figure(data=
                [go.Ohlc(x=dataset['date'],
                open=dataset['open'],
                high=dataset['high'],
                low=dataset['low'],
                close=dataset['close'],
                showlegend=True,
                name="predicted"),
                 go.Ohlc(x=dataset_true['date'],
                open=dataset_true['open'],
                high=dataset_true['high'],
                low=dataset_true['low'],
                close=dataset_true['close'],
                showlegend=True,
                name="true",
    increasing_line_color= 'blue', decreasing_line_color= 'yellow'
)])
fig.update_layout(
    autosize=False,
    width=1000,
    height=800,)
fig.update(layout_xaxis_rangeslider_visible=False)
st.plotly_chart(fig)