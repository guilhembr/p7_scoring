import uvicorn ##ASGI
from fastapi import FastAPI, HTTPException
import json
from pydantic import BaseModel, create_model
import joblib
import numpy as np
import pandas as pd
from sklearn.base import TransformerMixin
import shap


#######################################################################
# Loading data (to predict) and model
#---------------------------------------------------------------------

#loading data
df_train = pd.read_csv("./dashboard_data/df_train.csv")
df_test = pd.read_csv("./dashboard_data/df_test.csv")

#define list of cat and num features
list_cat_features = ["NAME_CONTRACT_TYPE",
    "CODE_GENDER",
    "FLAG_OWN_CAR",
    "FLAG_OWN_REALTY",
    "NAME_TYPE_SUITE",
    "NAME_INCOME_TYPE",
    "NAME_EDUCATION_TYPE",
    "NAME_FAMILY_STATUS",
    "NAME_HOUSING_TYPE",
    "FLAG_MOBIL",
    "FLAG_EMP_PHONE",
    "FLAG_WORK_PHONE",
    "FLAG_CONT_MOBILE",
    "FLAG_PHONE",
    "FLAG_EMAIL",
    "OCCUPATION_TYPE",
    "WEEKDAY_APPR_PROCESS_START",
    "REG_REGION_NOT_LIVE_REGION",
    "REG_REGION_NOT_WORK_REGION",
    "LIVE_REGION_NOT_WORK_REGION",
    "REG_CITY_NOT_LIVE_CITY",
    "REG_CITY_NOT_WORK_CITY",
    "LIVE_CITY_NOT_WORK_CITY",
    "ORGANIZATION_TYPE",
    "FONDKAPREMONT_MODE",
    "HOUSETYPE_MODE",
    "WALLSMATERIAL_MODE",
    "EMERGENCYSTATE_MODE",
    "FLAG_DOCUMENT_2",
    "FLAG_DOCUMENT_3",
    "FLAG_DOCUMENT_4",
    "FLAG_DOCUMENT_5",
    "FLAG_DOCUMENT_6",
    "FLAG_DOCUMENT_7",
    "FLAG_DOCUMENT_8",
    "FLAG_DOCUMENT_9",
    "FLAG_DOCUMENT_10",
    "FLAG_DOCUMENT_11",
    "FLAG_DOCUMENT_12",
    "FLAG_DOCUMENT_13",
    "FLAG_DOCUMENT_14",
    "FLAG_DOCUMENT_15",
    "FLAG_DOCUMENT_16",
    "FLAG_DOCUMENT_17",
    "FLAG_DOCUMENT_18",
    "FLAG_DOCUMENT_19",
    "FLAG_DOCUMENT_20",
    "FLAG_DOCUMENT_21"
]
list_num_features = [
    "CNT_CHILDREN",
    "AMT_INCOME_TOTAL",
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "DAYS_EMPLOYED",
    "DAYS_REGISTRATION",
    "DAYS_ID_PUBLISH",
    "REGION_RATING_CLIENT",
    "REGION_POPULATION_RELATIVE",
    "CNT_FAM_MEMBERS",
    "HOUR_APPR_PROCESS_START",
    "OWN_CAR_AGE",
    "EXT_SOURCE_1",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
    "APARTMENTS_AVG",
    "BASEMENTAREA_AVG",
    "YEARS_BEGINEXPLUATATION_AVG",
    "YEARS_BUILD_AVG",
    "COMMONAREA_AVG",
    "ELEVATORS_AVG",
    "ENTRANCES_AVG",
    "FLOORSMAX_AVG",
    "FLOORSMIN_AVG",
    "LANDAREA_AVG",
    "LIVINGAPARTMENTS_AVG",
    "LIVINGAREA_AVG",
    "NONLIVINGAPARTMENTS_AVG",
    "NONLIVINGAREA_AVG",
    "APARTMENTS_MODE",
    "YEARS_BEGINEXPLUATATION_MODE",
    "FLOORSMIN_MODE",
    "LIVINGAREA_MODE",
    "LANDAREA_MEDI",
    "TOTALAREA_MODE",
    "OBS_30_CNT_SOCIAL_CIRCLE",
    "DEF_30_CNT_SOCIAL_CIRCLE",
    "DEF_60_CNT_SOCIAL_CIRCLE",
    "DAYS_LAST_PHONE_CHANGE",
    "AMT_REQ_CREDIT_BUREAU_HOUR",
    "AMT_REQ_CREDIT_BUREAU_DAY",
    "AMT_REQ_CREDIT_BUREAU_WEEK",
    "AMT_REQ_CREDIT_BUREAU_MON",
    "AMT_REQ_CREDIT_BUREAU_QRT",
    "AMT_REQ_CREDIT_BUREAU_YEAR",
    "AGE_INT",
    "annuity_income_ratio",
    "credit_annuity_ratio",
    "credit_goods_price_ratio",
    "credit_downpayment"
]

#load serialized objects
# data_dict = joblib.load("./bin/data_dict.joblib")
ohe = joblib.load("./bin/ohe.joblib")
categorical_imputer = joblib.load("./bin/categorical_imputer.joblib")
simple_imputer = joblib.load("./bin/simple_imputer.joblib")
scaler = joblib.load("./bin/scaler.joblib")
model = joblib.load("./bin/model.joblib")

#---------------------------------------------------------------------
#data pre-processing (training set)

#SimpleImputing (most frequent) and ohe of categorical features
cat_array = categorical_imputer.transform(df_train[list_cat_features])
cat_array = ohe.transform(cat_array).todense()

#SimpleImputing (median) and StandardScaling of numerical features
num_array = simple_imputer.transform(df_train[list_num_features])
num_array = scaler.transform(num_array)

#concatenate
X_train = np.concatenate([cat_array, num_array], axis=1)
X_train = np.asarray(X_train)

#building dataframe with post-preprocessed data (training set)
cat_features_list_after_ohe = ohe.get_feature_names(list_cat_features).tolist()
features_list_after_prepr = cat_features_list_after_ohe + list_num_features
ohe_dataframe = pd.DataFrame(X_train, columns=features_list_after_prepr)

#---------------------------------------------------------------------
#data pre-processing (test set)

#SimpleImputing (most frequent) and ohe of categorical features
cat_array = categorical_imputer.transform(df_test[list_cat_features])
cat_array = ohe.transform(cat_array).todense()

#SimpleImputing (median) and StandardScaling of numerical features
num_array = simple_imputer.transform(df_test[list_num_features])
num_array = scaler.transform(num_array)

#concatenate
X = np.concatenate([cat_array, num_array], axis=1)
X = np.asarray(X)

#building dataframe with post-preprocessed data (testing set)
cat_features_list_after_ohe = ohe.get_feature_names(list_cat_features).tolist()
features_list_after_prepr_test = cat_features_list_after_ohe + list_num_features
ohe_dataframe_test = pd.DataFrame(X, columns=features_list_after_prepr_test)

#---------------------------------------------------------------------
#shap values
sub_sampled_train_data = shap.sample(ohe_dataframe, 50)
log_reg_explainer = shap.KernelExplainer(model.predict_proba, sub_sampled_train_data)

#######################################################################
#create fast API instance
app = FastAPI()

@app.get("/api/clients")
async def clients_id():
    """Endpoint to get all clients id

    Returns:
        list: clients_id
    """
    clients_id = df_test["SK_ID_CURR"].to_list()
    
    return {"clientsId": clients_id}  

@app.get("/api/clients/{id}")
async def client_details(id: int):
    """Endpoint to get client's details

    Args:
        id (int): client id in the test set

    Returns:
        client (dict): client's details
    """
    clients_id = df_test["SK_ID_CURR"].to_list()
    
    if id not in clients_id:
        raise HTTPException(status_code=404, detail="client's id not found")
    else:
        #filtering by client's id
        idx = df_test[df_test["SK_ID_CURR"] == id].index[0]
          
        client = {
            "clientId" : str(df_test.loc[idx,"SK_ID_CURR"]),
            "sexe": str(df_test.loc[idx,"CODE_GENDER"]),
            "statut familial": str(df_test.loc[idx,"NAME_FAMILY_STATUS"]),
            "enfants": str(df_test.loc[idx,"CNT_CHILDREN"]),
            "age": str(df_test.loc[idx,"AGE_INT"]),
            "statut pro": str(df_test.loc[idx,"NAME_INCOME_TYPE"]),
            "niveau d'études": str(df_test.loc[idx,"NAME_EDUCATION_TYPE"])
        }
        
        return client

@app.get("/api/clients/{id}/prediction")
async def predict(id: int):
    """Generate prediction and SHAP inputs for a selected client

    Args:
        id (int): SK_ID_CURR selected

    Raises:
        HTTPException: If SK_ID_CURR not found

    Returns:
        prediction_by_id (json) : dataset including prediction for the selected client
        log_reg_explainer (explainer) : SHAP Kernel Explainer
        shap_vals (list) : List of 2 arrays for 0 and 1 prediction classes
        features_list_after_prepr_test (list) : list of feature names
    """
    
    clients_id = df_test["SK_ID_CURR"].to_list()
    
    if id not in clients_id:
        raise HTTPException(status_code=404, detail="client's id not found")
    else:
       
        #prediction
        result_proba = model.predict_proba(X)
        y_pred_proba = result_proba[:, 1]
        # threshold = 0.48
        # y_pred = y_pred_proba > threshold
        # y_pred = y_pred.astype(float)
        
        df_test["pred"] = y_pred_proba
        df_test["pred"] = round(df_test["pred"].astype(np.float64),3)
        
        #filtering by client's id
        df_test_by_id = df_test[df_test["SK_ID_CURR"] == id]
        
        prediction_by_id = df_test_by_id.to_json()
        
        return prediction_by_id

#------------Cheat Sheet-----------------
    
#Run the API with uvicorn
#uvicorn api:app --reload  
    
#requirements.txt
#pip list --format=freeze > requirements.txt

#kill processes on port : kill -9 $(lsof -t -i:"8000")


#------------FUTURE IMPROVEMENTS-----------------

# #create model
# ScoringModel = create_model(
#     "ScoringModel",
#     **data_dict,
#     __base__=BaseModel,
# )

# ScoringModel.update_forward_refs()

# @app.post("/scoring")
# async def predict_scoring(item: ScoringModel):
#     item_dict = item.dict()

#     df = pd.DataFrame(data=[item_dict.values()], columns=item_dict.keys())
#     df = df.astype(object)

#     return json.dumps(model.predict_proba(X).tolist())


