"""Warm-start wider independent networks; validation-only acceptance per target."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import copy,json,joblib,numpy as np
from generate_data import ROOT,CASES
from train_models import features,metrics,TARGETS,INPUTS
from independent_model import IndependentRegressor
def widen(net,rng):
 n=copy.deepcopy(net);a,b=n.coefs_[0].shape[1],n.coefs_[1].shape[1]
 i=np.r_[np.arange(a),rng.integers(a,size=32)];j=np.r_[np.arange(b),rng.integers(b,size=32)]
 ci=np.bincount(i,minlength=a);cj=np.bincount(j,minlength=b)
 n.coefs_=[n.coefs_[0][:,i].copy(),n.coefs_[1][i][:,j]/ci[i,None],n.coefs_[2][j]/cj[j,None]]
 n.intercepts_=[n.intercepts_[0][i].copy(),n.intercepts_[1][j].copy(),n.intercepts_[2].copy()]
 # Break duplicated-neuron symmetry with a small fixed-seed perturbation.
 for w in n.coefs_:w+=rng.normal(0,1e-4,w.shape)
 n.set_params(hidden_layer_sizes=(len(i),len(j)),warm_start=True,max_iter=2500,max_fun=3500,tol=1e-12,alpha=1e-8)
 return n
def main():
 out=ROOT/'wider_refined';out.mkdir(exist_ok=True)
 for ci,case in enumerate(CASES):
  if (out/(case+'.joblib')).exists():continue
  ds=[np.genfromtxt(ROOT/f/(case+'.csv'),delimiter=',',names=True) for f in ['data','uniform_refined']]
  x=np.concatenate([features(d) for d in ds]);y=np.concatenate([np.column_stack([d[t] for t in TARGETS]) for d in ds]);spl=np.load(ROOT/'conserving_continued'/(case+'_split.npz'));tr=spl['train'];va=spl['validation'];te=spl['test']
  model=copy.deepcopy(joblib.load(ROOT/'independent_refined'/(case+'.joblib'))['model']);reg=model.regressor;xs=reg.xscale;ys=reg.yscale
  xx=xs.transform(model.transform_x(x));zz=ys.transform(model.transform_y(x,y));nets=[];records=[]
  for j,label in enumerate(['conductance','gate','body']):
   saved=out/(case+'_'+label+'.joblib')
   if saved.exists():nets.append(joblib.load(saved));continue
   base=reg.networks[j]
   def score(n):
    diff=(n.predict(xx[va]).reshape(-1)-zz[va,j])*ys.scale_[j]
    return float(np.mean(abs(10**np.clip(diff,-10,10)-1)))
   best=copy.deepcopy(base);bestscore=score(base);net=widen(base,np.random.default_rng(20261130+ci*3+j))
   print(case,label,'baseline mean magnitude error %',100*bestscore,flush=True)
   for stage in range(3):
    checkpoint=out/(case+'_'+label+'_stage'+str(stage)+'.joblib')
    if checkpoint.exists():net=joblib.load(checkpoint)
    else:
     print(case,label,stage,'training',flush=True);net.fit(xx[tr],zz[tr,j]);joblib.dump(net,checkpoint)
    s=score(net);records.append(dict(target=label,stage=stage,validation_mean_magnitude_error_percent=100*s));print(case,label,stage,'validation mean %',100*s,flush=True)
    if s<bestscore:bestscore=s;best=copy.deepcopy(net)
    (out/(case+'_history.json')).write_text(json.dumps(records,indent=2))
   joblib.dump(best,saved);nets.append(best)
  model.regressor=IndependentRegressor(xs,ys,nets)
  joblib.dump(dict(model=model,method='wider_independent_conserving_MLP',output='physical_signed_current',inputs=INPUTS,targets=TARGETS),out/(case+'.joblib'))
  (out/(case+'_metrics.json')).write_text(json.dumps(dict(validation=metrics(y[va],model.predict(x[va])),test=metrics(y[te],model.predict(x[te]))),indent=2))
 (out/'complete.json').write_text('{"completed":true}')
if __name__=='__main__':main()
