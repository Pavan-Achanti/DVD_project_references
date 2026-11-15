"""Current-conserving signed transistor surrogate, with smooth conductance target."""
import numpy as np
class ConservingModel:
 def __init__(self,regressor,case):self.regressor=regressor;self.case=case
 def transform_x(self,x):
  # Canonical drain/source ordering exploits symmetry of the supplied device.
  z=x[:,:10].copy();z[:,3]=np.minimum(x[:,3],x[:,4]);z[:,4]=np.maximum(x[:,3],x[:,4])
  return np.column_stack([z,1/z[:,1],z[:,3]*z[:,0],z[:,4]*z[:,0]])
 def transform_y(self,x,y):
  delta=(x[:,3]-x[:,4])*x[:,0]
  conductance=(y[:,0]-y[:,2])/(2*delta)
  return np.log10(np.maximum(np.column_stack([conductance,abs(y[:,1]),abs(y[:,3])])/x[:,2,None],1e-30))
 def fit(self,x,y):self.regressor.fit(self.transform_x(x),self.transform_y(x,y));return self
 def predict(self,x):
  a=10**np.clip(self.regressor.predict(self.transform_x(x)),-30,1)*x[:,2,None]
  ig=a[:,1]*(1 if self.case in ['nmos_on','pmos_off'] else -1)
  ib=a[:,2]*(-1 if self.case.startswith('nmos') else 1)
  q=a[:,0]*(x[:,3]-x[:,4])*x[:,0]
  return np.column_stack([q-(ig+ib)/2,ig,-q-(ig+ib)/2,ib])
