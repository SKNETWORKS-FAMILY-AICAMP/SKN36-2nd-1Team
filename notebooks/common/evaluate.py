from sklearn.metrics import roc_auc_score, average_precision_score, classification_report, confusion_matrix



def get_score(model, x, y,threshold=0.5) -> dict:

    proba = model.predict_proba(x)[:,1]
    #pred = model.predict(x)
    pred = (proba >=threshold).astype(int)
    conf_mx = confusion_matrix(y, pred,normalize='true')
    report = classification_report(y,pred)
    auc_score = roc_auc_score(y, proba)
    pr_auc = average_precision_score(y, proba)

    results = {
        "conf_mx" : conf_mx,
        "report" : report,
        "auc_score" : auc_score,
        "pr_auc" : pr_auc
    }
    return results

# train_score, test_score 
def evaluate(model, trains:list, targets:list):

    x_train, y_train = trains
    x_test, y_test = targets
 
    return {
        "train_score" : get_score(model, x_train, y_train),
        "test_score" : get_score(model, x_test, y_test)
    }
