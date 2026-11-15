"""Independent regression of zero-bias-normalized targets; transistor-only fit."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import copy,json,joblib,numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from generate_data import ROOT,CASES
from train_models import features,metrics,TARGETS,INPUTS
from independent_model import IndependentRegressor
from normalized_model import NormalizedModel
def main():
 out=ROOT/'normalized_refined';out.mkdir(exist_ok=True)
 for ci,case in enumerate(CASES):
  if (out/(case+'.joblib')).exists():continue
  ds=[np.genfromtxt(ROOT/f/(case+'.csv'),delimiter=',',names=True) for f in ['data','uniform_refined']]
  x=np.concatenate([features(d) for d in ds]);y=np.concatenate([np.column_stack([d[t] for t in TARGETS]) for d in ds]);spl=np.load(ROOT/'conserving_continued'/(case+'_split.npz'));tr=spl['train'];va=spl['validation'];te=spl['test']
  model=NormalizedModel(None,case);rawx=model.transform_x(x);rawy=model.transform_y(x,y)
  xs=StandardScaler().fit(rawx[tr]);ys=StandardScaler().fit(rawy[tr]);xx=xs.transform(rawx);zz=ys.transform(rawy);nets=[];records=[]
  for j,label in enumerate(['conductance','gate','body']):
   saved=out/(case+'_'+label+'.joblib')
   if saved.exists():nets.append(joblib.load(saved));continue
   net=MLPRegressor(hidden_layer_sizes=(64,64),activation='tanh',solver='lbfgs',warm_start=True,max_iter=2500,max_fun=3500,tol=1e-12,alpha=1e-8,random_state=20261202+ci*3+j)
   best=None;bestscore=float('inf')
   for stage in range(3):
    checkpoint=out/(case+'_'+label+'_stage'+str(stage)+'.joblib')
    if checkpoint.exists():net=joblib.load(checkpoint)
    else:
     print(case,label,stage,'training',flush=True);net.fit(xx[tr],zz[tr,j]);joblib.dump(net,checkpoint)
    diff=(net.predict(xx[va])-zz[va,j])*ys.scale_[j];s=float(np.mean(abs(10**np.clip(diff,-10,10)-1)))
    records.append(dict(target=label,stage=stage,validation_mean_magnitude_error_percent=100*s));print(case,label,stage,'validation mean %',100*s,flush=True)
    if s<bestscore:bestscore=s;best=copy.deepcopy(net)
    (out/(case+'_history.json')).write_text(json.dumps(records,indent=2))
   joblib.dump(best,saved);nets.append(best)
  model.regressor=IndependentRegressor(xs,ys,nets)
  joblib.dump(dict(model=model,method='zero_bias_normalized_MLP',output='physical_signed_current',inputs=INPUTS,targets=TARGETS),out/(case+'.joblib'))
  (out/(case+'_metrics.json')).write_text(json.dumps(dict(validation=metrics(y[va],model.predict(x[va])),test=metrics(y[te],model.predict(x[te]))),indent=2))
 (out/'complete.json').write_text('{"completed":true}')
if __name__=='__main__':main()
