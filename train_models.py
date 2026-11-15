"""Four-method baseline; validation-only model selection, untouched final test."""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import csv,json,time
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler,PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from sklearn.ensemble import ExtraTreesRegressor,HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import r2_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generate_data import ROOT,CASES,PARAMS
from current_model import CurrentModel

INPUTS=['vdd','temp','w','vd','vs']+PARAMS
TARGETS=['id','ig','is','ib']

def features(data):
    x=np.column_stack([data[k] for k in INPUTS])
    # Dimensionless physical inputs improve conditioning; no target-derived features.
    x[:,1]=(x[:,1]+273.15)/300
    x[:,2]/=45e-9
    x[:,3]/=x[:,0];x[:,4]/=x[:,0]
    for j,p in enumerate(PARAMS,5):
        x[:,j]/={'vth0':1,'toxe':1e-9,'ndep':1e18,'u0':.01,'xj':1e-8}[p]
    return np.column_stack([x,x[:,3]-x[:,4],abs(x[:,3]-x[:,4]),np.log10(np.maximum(abs(x[:,3]-x[:,4]),1e-12)),np.minimum(x[:,3],x[:,4]),np.maximum(x[:,3],x[:,4]),1/x[:,1]])

def metrics(y,p):
    err=100*abs(p-y)/np.maximum(abs(y),1e-18)
    return dict(r2=float(r2_score(y,p)),median_error_percent=float(np.median(err)),p95_error_percent=float(np.percentile(err,95)),per_terminal={k:dict(r2=float(r2_score(y[:,i],p[:,i])),median_error_percent=float(np.median(err[:,i])),p95_error_percent=float(np.percentile(err[:,i],95))) for i,k in enumerate(TARGETS)})

def main():
    out=ROOT/'ml';out.mkdir(exist_ok=True); tables=[];final={}
    for case in CASES:
        path=ROOT/'data'/(case+'.csv')
        while not path.exists(): time.sleep(5)
        # Generation closes each file before progressing; wait for full row count.
        while True:
            try:
                data=np.genfromtxt(path,delimiter=',',names=True)
                if len(data)>=10000:break
            except ValueError:pass
            time.sleep(5)
        x=features(data);y=np.column_stack([data[k] for k in TARGETS])
        train,rest=train_test_split(np.arange(len(x)),test_size=.3,random_state=20261109)
        val,test=train_test_split(rest,test_size=.5,random_state=20261109)
        np.savez(out/(case+'_split.npz'),train=train,validation=val,test=test)
        # Fixed invertible signed transform preserves negative currents and zero.
        scale=np.full(4,1e-15); z=np.arcsinh(y/scale)
        models={
          'polynomial_ridge':make_pipeline(StandardScaler(),PolynomialFeatures(3),Ridge(alpha=.01)),
          'extra_trees':ExtraTreesRegressor(n_estimators=150,min_samples_leaf=1,n_jobs=2,random_state=20261109),
          'hist_gradient_boosting':MultiOutputRegressor(HistGradientBoostingRegressor(max_iter=150,max_leaf_nodes=31,l2_regularization=.1,random_state=20261109)),
          'neural_network':make_pipeline(StandardScaler(),MLPRegressor(hidden_layer_sizes=(96,96),activation='tanh',max_iter=500,early_stopping=True,validation_fraction=.1,n_iter_no_change=30,random_state=20261109))}
        winner=None;score=float('inf')
        for name,model in models.items():
            print(case,name,'training',flush=True);start=time.time();model=CurrentModel(model);model.fit(x[train],y[train]);pred=model.predict(x[val])
            m=metrics(y[val],pred);tables.append(dict(case=case,method=name,seconds=time.time()-start,**m))
            print(case,name,json.dumps(m),flush=True)
            (out/'validation_comparison.json').write_text(json.dumps(tables,indent=2))
            joblib.dump(model,out/(case+'_'+name+'_candidate.joblib'))
            if m['median_error_percent']<score:
                score=m['median_error_percent'];winner=dict(model=model,method=name,scale=scale,inputs=INPUTS,targets=TARGETS,output='physical_signed_current')
        joblib.dump(winner,out/(case+'.joblib'))
        pred=winner['model'].predict(x[test])
        final[case]=dict(method=winner['method'],**metrics(y[test],pred))
        (out/'test_metrics.json').write_text(json.dumps(final,indent=2))
        fig,axes=plt.subplots(2,2,figsize=(9,8))
        for j,ax in enumerate(axes.flat):
            ax.scatter(abs(y[test,j]),abs(pred[:,j]),s=3,alpha=.3)
            ax.set_xscale('log');ax.set_yscale('log');ax.set_title(TARGETS[j]);ax.set_xlabel('SPICE magnitude (A)');ax.set_ylabel('ML magnitude (A)')
            lo=max(min(abs(y[test,j]).min(),abs(pred[:,j]).min()),1e-25);hi=max(abs(y[test,j]).max(),abs(pred[:,j]).max());ax.plot([lo,hi],[lo,hi],'k--')
        fig.suptitle(case+' — held-out test, magnitudes shown');fig.tight_layout();fig.savefig(out/(case+'_parity.png'),dpi=150);plt.close(fig)
    with (out/'validation_comparison.csv').open('w',newline='') as f:
        fields=['case','method','seconds','r2','median_error_percent','p95_error_percent'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(tables)

if __name__=='__main__':main()
