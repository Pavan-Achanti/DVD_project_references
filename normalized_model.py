"""Factor known zero-bias limits before fitting log leakage magnitudes."""
import numpy as np
from conserving_model import ConservingModel
class NormalizedModel(ConservingModel):
 def factors(self,x):
  vd=x[:,3]*x[:,0];vs=x[:,4]*x[:,0];vb=x[:,0] if self.case.startswith('pmos') else np.zeros(len(x))
  vg=x[:,0] if self.case in ['nmos_on','pmos_off'] else np.zeros(len(x))
  gate=abs(vg-vd)+abs(vg-vs) if self.case.endswith('_off') else np.ones(len(x))
  # ON devices may still have gate-to-body tunnelling at zero junction bias.
  body=abs(vb-vd)+abs(vb-vs) if self.case.endswith('_off') else np.ones(len(x))
  return np.column_stack([np.ones(len(x)),gate,body])
 def transform_y(self,x,y):return super().transform_y(x,y)-np.log10(np.maximum(self.factors(x),1e-30))
 def predict(self,x):
  a=10**np.clip(self.regressor.predict(self.transform_x(x)),-30,1)*x[:,2,None]*self.factors(x)
  ig=a[:,1]*(1 if self.case in ['nmos_on','pmos_off'] else -1)
  ib=a[:,2]*(-1 if self.case.startswith('nmos') else 1)
  q=a[:,0]*(x[:,3]-x[:,4])*x[:,0]
  return np.column_stack([q-(ig+ib)/2,ig,-q-(ig+ib)/2,ib])
