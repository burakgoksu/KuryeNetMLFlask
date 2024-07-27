import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_file
import pandas as pd
from flask_httpauth import HTTPBasicAuth
from AlertAvailableSessions import AlertAvailableSessions
from CatBoostModel import KuryeNetML
from datetime import datetime
from pytz import timezone
import threading


app = Flask(__name__)

tz = timezone('Europe/Istanbul') # UTC, Asia/Shanghai, Europe/Berlin

def timetz(*args):
    return datetime.now(tz).timetuple()

logging.Formatter.converter = timetz

# Loglama için temel yapılandırmayı ayarla
logging.basicConfig(level=logging.INFO)

# Rotating log dosyaları oluştur, 10MB'da bir yeni dosya oluştur ve en fazla 10 dosya sakla
file_handler = RotatingFileHandler('KuryeNetApp.log', maxBytes=80000 * 80000, backupCount=10)
file_handler.setLevel(logging.INFO)  # INFO ve üzeri seviyedeki logları yakala

# Log mesajları için bir format belirle
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Flask app logger'ına file handler'ı ekle
app.logger.addHandler(file_handler)

auth = HTTPBasicAuth()

kuryeNetML = KuryeNetML('KaggleData.csv','catboost_model.cbm')


alert_empty_session = None
alert_thread = None


@auth.verify_password
def verify_password(username, password):
    if username == 'admin' and password == 'admin':
        app.logger.info(f"Method: verify_password, Username: {username}, Password: {password}, Basic Auth successful.")
        return True
    else:
        app.logger.error(f"Method: verify_password, Username: {username}, Password: {password}, Basic Auth failed.")
        return False

@app.route('/available_sessions_logs', methods=['GET'])
def show_available_sessions_logs():
    log_file_path = 'AlertAvailableSessions.log'
    return send_file(log_file_path, as_attachment=True)

@app.route('/start_available_sessions_bot', methods=['GET'])
def start_available_sessions_boy():
    global alert_empty_session, alert_thread
    if alert_empty_session is None:
        alert_empty_session = AlertAvailableSessions(
            link1="https://online.spor.istanbul/uyegiris",
            link2="https://online.spor.istanbul/uyespor",
            txt_file1="UmraniyeCakmakYuzmeHavuzuSeans.txt",
            txt_file2="UygunSeanslar.txt",
            headless=False,
            sender_email="gogsub58365@gmail.com",
            sender_password="hnma axon amcw sumr",
            receiver_email="gogsub58365@gmail.com"
        )
    if alert_thread is None or not alert_thread.is_alive():
        alert_thread = threading.Thread(target=alert_empty_session.start)
        alert_thread.start()
        app.logger.info('AlertAvailableSessions bot started')
        return 'AlertAvailableSessions bot started'
    else:
        return 'AlertAvailableSessions bot is already running'

@app.route('/stop_available_sessions_bot', methods=['GET'])
def stop_available_sessions_boy():
    global alert_empty_session, alert_thread
    if alert_empty_session is not None:
        alert_empty_session.stop()
        alert_empty_session = None
        alert_thread = None
        app.logger.info('AlertAvailableSessions bot stopped')
        return 'AlertAvailableSessions bot stopped'
    else:
        return 'AlertAvailableSessions bot is not running'

@app.route('/logs',methods=['GET'])
@auth.login_required
def show_logs():
    log_file_path = 'KuryeNetApp.log'
    return send_file(log_file_path, as_attachment=True)

@app.route('/predict', methods=['POST'])
@auth.login_required
def predict():
    try:

        # JSON olarak gönderilen veriyi al
        data = request.json
        print(data)

        Delivery_Person_Age = data.get('delivery_Person_Age',25)
        print(Delivery_Person_Age)
        Weather_Condition = data.get('weather_Condition','Sunny')
        Road_Traffic_Density = data.get('road_Traffic_Density','Low')
        Type_Of_Order = data.get('type_Of_Order','Meal')
        Type_Of_Vehicle = data.get('type_Of_Vehicle','Motorcycle')
        Multiple_Deliveries = data.get('multiple_Deliveries',0)
        City = data.get('city','Metropolitian')
        Distance = data.get('distance',0)
        Day_Type = data.get('day_Type','Weekday')
        Time_Category = data.get('time_Category','Noon')

        prediction_value = kuryeNetML.Prediction(Delivery_Person_Age,Weather_Condition,Road_Traffic_Density,Type_Of_Order,Type_Of_Vehicle,Multiple_Deliveries,City,Distance,Day_Type,Time_Category)

        app.logger.info(f"Method: predict, Data: {data}, Prediction Value: {prediction_value}, Rounded: {round(prediction_value)}, Prediction request successful.")
        return jsonify({'Prediction':prediction_value,
                        'PredictionRound':round(prediction_value)})

    except Exception as e:
        app.logger.error(f"Method: predict, Error: {str(e)}, Prediction request unsuccessful.")

        return jsonify({'error': str(e)})


@app.route('/write_data', methods=['POST'])
@auth.login_required
def write_data():
    try:
        # JSON olarak gönderilen veriyi al
        data = request.json
        # Veriyi DataFrame'e dönüştür (tek bir nesne için bir liste içinde)
        data_df = pd.DataFrame([data])  # Anahtarları sütun adlarına, değerleri ise satır değerlerine dönüştürür

        # Dosyanın var olup olmadığını kontrol et ve buna göre header'ı ayarla
        file_exists = os.path.exists('KuryeNetData.csv')

        # Veriyi CSV dosyasına yaz
        # Eğer dosya yoksa, header yazılır; varsa, yazılmaz
        data_df.to_csv('KuryeNetData.csv', mode='a', header=not file_exists, index=False)
        app.logger.info(f"Method: write_data , Data: {data}, Data was written successful on KuryeNetData.csv file.")
        return jsonify({'message': 'Data successfully written to KuryeNetData.csv'})
    except Exception as e:
        app.logger.error(f"Method: write_data, Error: {str(e)}, Data unsuccessfully written to KuryeNetData.csv.")
        return jsonify({'error': str(e)})



@app.route('/retrain_model', methods=['POST'])
@auth.login_required
def retrain_model():
    try:
        # Yeni verileri içeren CSV dosyasını kontrol et
        new_data_path = 'KuryeNetData.csv'
        if not os.path.exists(new_data_path):
            app.logger.error(f"Method: retrain_model, Error: {new_data_path}, KuryeNetData file does not exist.")
            return jsonify({'error': 'KuryeNetData file does not exist.'})

        # İlk CSV dosyasını oku
        df1 = pd.read_csv('KaggleData.csv')

        # İkinci CSV dosyasını oku
        df2 = pd.read_csv('KuryeNetData.csv')

        # İki DataFrame'i satır bazında birleştir
        birlesik_df = pd.concat([df1, df2], ignore_index=True)

        # Birleştirilmiş DataFrame'i yeni bir CSV dosyasına yaz
        birlesik_df.to_csv('AllData.csv', index=False)

        kuryeNetML.TrainCatBoostModel()

        app.logger.info(f"Method: retrain_model, Model: {kuryeNetML.modelFile}, Model has been retrained with {kuryeNetML.csvFile}.")
        return jsonify({'message': 'Model: '+ kuryeNetML.modelFile+ ' has been retrained with ' + kuryeNetML.csvFile})
    except Exception as e:
        app.logger.error(f"Method: retrain_model, Error: {str(e)}, Model has not been retrained with {kuryeNetML.csvFile}.")

        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
