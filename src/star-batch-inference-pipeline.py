import os
import modal
    
LOCAL=False

if LOCAL == False:
   stub = modal.Stub()
   hopsworks_image = modal.Image.debian_slim().pip_install(["hopsworks","joblib","seaborn","scikit-learn==1.1.1","dataframe-image"])
   @stub.function(image=hopsworks_image, schedule=modal.Period(days=1), secret=modal.Secret.from_name("HOPSWORKS_API_KEY"))
   def f():
       g()

def g():
    import pandas as pd
    import hopsworks
    import joblib
    import datetime
    from PIL import Image
    from datetime import datetime
    import dataframe_image as dfi
    from sklearn.metrics import confusion_matrix
    from matplotlib import pyplot
    import seaborn as sns
    import requests

    project = hopsworks.login(project="ID2223_23_lab1")
    fs = project.get_feature_store()
    
    mr = project.get_model_registry()
    model = mr.get_model("star_model", version=1)
    model_dir = model.download()
    model = joblib.load(model_dir + "/star_model.pkl")
    
    feature_view = fs.get_feature_view(name="star", version=1)
    batch_data = feature_view.get_batch_data()
    
    y_pred = model.predict(batch_data)
    #print(y_pred)
    offset = 51
    star = y_pred[y_pred.size-offset]
    star_url = "https://raw.githubusercontent.com/bokuan/ID2223/main/res/" + star.lower() + ".jpg"
    print("Star type predicted: " + star)
    img = Image.open(requests.get(star_url, stream=True).raw)            
    img.save("./latest_star.png")
    dataset_api = project.get_dataset_api()    
    dataset_api.upload("./latest_star.png", "Resources/images", overwrite=True)
   
    star_fg = fs.get_feature_group(name="star", version=1)
    df = star_fg.read() 
    #print(df)
    label = df.iloc[-offset]["type"]
    label_url = "https://raw.githubusercontent.com/bokuan/ID2223/main/res/" + label.lower() + ".jpg"
    print("Star actual: " + label)
    img = Image.open(requests.get(label_url, stream=True).raw)            
    img.save("./actual_star.png")
    dataset_api.upload("./actual_star.png", "Resources/images", overwrite=True)
    
    monitor_fg = fs.get_or_create_feature_group(name="star_predictions",
                                                version=1,
                                                primary_key=["datetime"],
                                                description="Star type Prediction/Outcome Monitoring"
                                                )
    
    now = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    data = {
        'prediction': [star],
        'label': [label],
        'datetime': [now],
       }
    monitor_df = pd.DataFrame(data)
    monitor_fg.insert(monitor_df, write_options={"wait_for_job" : False})
    
    history_df = monitor_fg.read()
    # Add our prediction to the history, as the history_df won't have it - 
    # the insertion was done asynchronously, so it will take ~1 min to land on App
    history_df = pd.concat([history_df, monitor_df])


    star_df_recent = history_df.tail(4)
    dfi.export(star_df_recent, './star_df_recent.png', table_conversion = 'matplotlib')
    dataset_api.upload("./star_df_recent.png", "Resources/images", overwrite=True)
    
    predictions = history_df[['prediction']]
    labels = history_df[['label']]

    # Only create the confusion matrix when our iris_predictions feature group has examples of all 3 iris flowers
    print("Number of different star types predictions to date: " + str(predictions.value_counts().count()))
    if predictions.value_counts().count() == 3:
        results = confusion_matrix(labels, predictions)
    
        df_cm = pd.DataFrame(results, ['GALAXY', 'QSO','STAR'],
                             ['GALAXY', 'QSO','STAR'])
    
        cm = sns.heatmap(df_cm, annot=True)
        fig = cm.get_figure()
        fig.savefig("./star_confusion_matrix.png")
        dataset_api.upload("./star_confusion_matrix.png", "Resources/images", overwrite=True)
    else:
        print("You need 3 different star predictions to create the confusion matrix.")
        print("Run the batch inference pipeline more times until you get 3 different star predictions") 


if __name__ == "__main__":
    if LOCAL == True :
        g()
    else:
        with stub.run():
            f.remote()


