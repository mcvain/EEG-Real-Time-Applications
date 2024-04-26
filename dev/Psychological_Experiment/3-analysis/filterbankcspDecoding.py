###############################################
####Filter Bank -> CSP -> Classification########
###############################################

"""
1. **Feature Extraction**: Filter bank band pass channels will be used as main features.  To extract the features, we are going to use a **filter-bank of band-pass channels**, namely 4-8Hz, 6-10Hz, 8-12Hz, etc.
2. **Feature Selection**: Common Spatial Pattern will help find the components that exhibit maximum variances which helps project the data into most discriminating features (i.e., features with maximum variance).  Each pair of band-pass and CSP filters computes the CSP features, which are specific to the band-pass frequency range.
3. **Classification**
"""

import pandas as pd

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedShuffleSplit

from mne import Epochs, find_events
from mne.decoding import CSP, Vectorizer, Scaler

from pyriemann.classification import MDM
from pyriemann.tangentspace import TangentSpace
from pyriemann.estimation import Covariances

from collections import OrderedDict
import helper as helper

import matplotlib.pyplot as plt
plt.rcParams.update({'figure.max_open_warning': 0})
import seaborn as sns

def decode(raw, event_id, tmin, tmax, band_width, band_overlap, low_freq, n_filters):

    pipeline_list = []
    step = band_width - band_overlap  

    bands = range(low_freq, low_freq + n_filters * step, step)

    raw_list = []
    for low in bands:
        raw_list.append(raw.copy().filter(low, low+band_width, method='iir'))

    # Extract epochs
    epoch_list = []

    for raw_bank in raw_list:

        #from 1 to 2.5 s after stimulus onset, to avoid classifying the ERP)
        epoch = helper.getEpochs(raw_bank, event_id, tmin=tmin, tmax=tmax)
        epoch_list.append(epoch)

    #loop through each filter bank of epoch and perform modeling
    #this will take around 30 minutes, so sip a coffee and wait
    for epoch in epoch_list:
        result = model(epoch)
        plot(result, low_freq, band_width)
        low_freq = low_freq + 2  #for only plotting purpose


"""
- **CSP + Classifier** :  Common Spatial Patterns + Regularized Linear Discriminat Analysis. This is a very common EEG analysis pipeline.
- **Cov + MDM**: Covariance + MDM. A very simple, yet effective (for low channel count), Riemannian geometry classifier.
- **Cov + TS** :  Covariance + Tangent space mapping. One of the most reliable Riemannian geometry-based pipelines.

Evaluation is done through cross-validation, with area-under-the-curve (AUC) as metric (AUC is probably the best metric for binary and unbalanced classification problem)

*Note: because we're doing machine learning here, the following cell may take a while to complete*

*Note: Scikit-learn API provides functionality to chain transformers and estimators by using sklearn.pipeline.Pipeline. We can construct decoding pipelines and perform cross-validation and grid-search. However scikit-learn transformers and estimators generally expect 2D data (n_samples * n_features), whereas MNE transformers typically output data with a higher dimensionality (e.g. n_samples * n_channels * n_times). A Vectorizer or Covariances or CSP therefore needs to be applied between the MNE and the scikit-learn steps.
"""
def model(epoch):

    epoch.pick_types(eeg=True)
    X = epoch.get_data() #n_epochs * n_channel * n_time_samples  
     #CSP will take in data in this form and create features of 2d
    y = epoch.events[:, -1]

    clfs = OrderedDict()
    
    lda = LDA(shrinkage='auto', solver='eigen') #Regularized LDA
    svc = SVC()
    lr = LogisticRegression()
    knn = KNeighborsClassifier(n_neighbors=3) #you would want to optimize
    nb = GaussianNB()
    rf = RandomForestClassifier(n_estimators=50, random_state=1)
    mdm = MDM()
    ts = TangentSpace()
    vec = Vectorizer()
    scale = Scaler(epoch.info)  #by default, CSP already does this, but if you use Vectorizer, you hve to do it before Vectorizing
    csp = CSP(n_components=3, reg=0.3) #feature extraction, reg is used when data is not PD (positive definite)

    #clfs['Vectorizer + LDA'] = Pipeline([('Scaler', scale), ('Vectorizer', vec), ('Model', lda)])
    clfs['CSP + LDA'] = Pipeline([('CSP', csp), ('Model', lda)])
    clfs['CSP + SVC'] = Pipeline([('CSP', csp), ('Model', svc)])
    clfs['CSP + LR'] = Pipeline([('CSP', csp), ('Model', lr)])
    clfs['CSP + KNN'] = Pipeline([('CSP', csp), ('Model', knn)])
    clfs['CSP + NB'] = Pipeline([('CSP', csp), ('Model', nb)])
    clfs['CSP + RF'] = Pipeline([('CSP', csp), ('Model', rf)])
    clfs['Cov + MDM'] = Pipeline([('Cov', Covariances('oas')), ('Model', mdm)]) #oas is needed for non-PD matrix
    #clfs['Cov + TS'] = Pipeline([('Cov', Covariances('oas')), ('Model', ts)]) #oas is needed for non-PD matrix
    #not sure why TS is not working....

    auc = []
    methods = []

    # define cross validation (i put 10 to reduce time for demo)
    cv = StratifiedShuffleSplit(n_splits=10, test_size=0.25, 
                            random_state=42)

    for m in clfs:
        print("+", end="") #to know it's working, no newline
        try:
            res = cross_val_score(clfs[m], X, y, scoring='roc_auc', 
                              cv=cv, n_jobs=-1)
            auc.extend(res)
            methods.extend([m]*len(res))
        except:
            pass
    
    results = pd.DataFrame(data=auc, columns=['AUC'])
    results['Method'] = methods

    return results

def plot(df, low_freq, band_width):
    figure = plt.figure(figsize=[8,4])
    plt.title("%d - %d Hz" %(low_freq, low_freq + band_width))
    sns.barplot(data=df, x='AUC', y='Method')
    plt.xlim(0.4, 1)    
    sns.despine()


