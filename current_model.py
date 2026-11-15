"""Signed log-magnitude regression with a separately learned current direction."""
import numpy as np
from sklearn.tree import DecisionTreeClassifier

class CurrentModel:
    def __init__(self, regressor):
        self.regressor=regressor
        self.direction=DecisionTreeClassifier(max_depth=10,min_samples_leaf=3,random_state=20261109)
    def fit(self,x,y):
        self.direction.fit(x,(y>=0).astype(int))
        self.regressor.fit(x,np.log10(np.maximum(abs(y),1e-25)/x[:,2,None]))
        return self
    def predict(self,x):
        magnitude=10**np.clip(self.regressor.predict(x),-30,0)*x[:,2,None]
        return magnitude*(2*self.direction.predict(x)-1)
