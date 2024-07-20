from catboost import CatBoostRegressor
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

# Veri setini yükle
df = pd.read_csv('KaggleData.csv')
# Bağımsız değişkenler (X) ve bağımlı değişken (y) seçimi
X = df[['Delivery_Person_Age', 'Weather_Condition', 'Road_Traffic_Density', 'Type_Of_Order', 'Type_Of_Vehicle', 'Multiple_Deliveries', 'City', 'Distance', 'Day_Type', 'Time_Category']]
y = df['Time_Taken']

# Kategorik özellikleri sayısal hale getir
X = pd.get_dummies(X)

# Eğitim ve test setlerine ayırma
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# CatBoost modelini oluştur
cb_model = CatBoostRegressor(iterations=1000, learning_rate=0.01, depth=8, loss_function='RMSE', verbose=100,l2_leaf_reg= 1)

# Kategorik özelliklerin indekslerini bul
cat_features = np.where(X_train.dtypes == 'object')[0]

# Modeli eğit
cb_model.fit(X_train, y_train, cat_features=cat_features)

# Test seti üzerinde tahminler yap
predictions = cb_model.predict(X_test)

# Modelin performansını değerlendir
rmse = mean_squared_error(y_test, predictions, squared=False)
r2 = r2_score(y_test, predictions)
mse = mean_squared_error(y_test, predictions)
print(f"MSE: {mse}")
print(f"RMSE: {rmse}")
print(f"R^2: {r2}")

# Modeli kaydet
cb_model.save_model('catboost_model.cbm')


# Modeli yükle
loaded_cb_model = CatBoostRegressor()
loaded_cb_model.load_model('catboost_model.cbm')


# Yeni bir veri noktası oluştur
new_data = {
    'Delivery_Person_Age': [25],
    'Weather_Condition': ['Cloudy'],
    'Road_Traffic_Density': ['Low'],
    'Type_Of_Order': ['Meal'],
    'Type_Of_Vehicle': ['Car'],
    'Multiple_Deliveries': [0],
    'City': ['Metropolitian'],
    'Distance': [18938],
    'Day_Type': ['Weekday'],
    'Time_Category': ['Evening']
}

# Yeni veri noktasını DataFrame'e dönüştür
new_data_df = pd.DataFrame(new_data)

# Modelin eğitildiği veri setindeki kategorik özellikler için one-hot encoding uygula
# Burada, `X` model eğitiminde kullanılan özelliklerin orijinal DataFrame'idir.
# `pd.get_dummies` fonksiyonunu kullanarak, eğitim setindeki kategorik özelliklere uygulanan one-hot encoding işlemini yeni veriye de uygulayabiliriz.
new_data_processed = pd.get_dummies(new_data_df)
# Eğitim setindeki tüm one-hot encoded sütunları elde etmek için kullanılan kod:
X_encoded_columns = pd.get_dummies(X).columns
# Yeni veride eksik olan sütunları sıfır değeri ile doldur:
for col in X_encoded_columns:
    if col not in new_data_processed.columns:
        new_data_processed[col] = 0
# Sütun sırasını eğitim seti ile aynı hale getir
new_data_processed = new_data_processed[X_encoded_columns]

# Modeli kullanarak yeni veri noktası için tahmin yap
prediction = loaded_cb_model.predict(new_data_processed)

print(f"Tahmini Süre: {prediction[0]} dakika")

