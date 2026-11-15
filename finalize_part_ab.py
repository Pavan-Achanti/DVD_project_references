"""Select by transistor validation only, batch gate prediction, export auditable results."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import csv,json,time,hashlib
import numpy as np
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generate_data import ROOT,CASES
from train_models import features,metrics,TARGETS
from gates import devices,predict

def write_csv(path,rows):
    tmp=path.with_suffix('.tmp')
    with tmp.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    tmp.replace(path)

def main():
    out=ROOT/'final_results';out.mkdir(exist_ok=True);models_dir=ROOT/'selected_models';models_dir.mkdir(exist_ok=True)
    sources=['ml','neural_refined','neural_continued']
    if (ROOT/'uniform_refined').exists():sources.append('uniform_refined')
    if (ROOT/'conserving_refined').exists():sources.append('conserving_refined')
    if (ROOT/'conserving_continued').exists():sources.append('conserving_continued')
    if (ROOT/'residual_refined').exists():sources.append('residual_refined')
    if (ROOT/'independent_refined').exists():sources.append('independent_refined')
    if (ROOT/'wider_refined').exists():sources.append('wider_refined')
    if (ROOT/'normalized_refined').exists():sources.append('normalized_refined')
    for folder in sources:
        missing=[c for c in CASES if not (ROOT/folder/(c+'.joblib')).exists()]
        if missing:raise RuntimeError(f'Missing models in {folder}: {missing}. Complete that training stage first.')
    bundles={};model_metrics={};comparisons=[]
    for case in CASES:
        data=np.genfromtxt(ROOT/'data'/(case+'.csv'),delimiter=',',names=True);x=features(data);y=np.column_stack([data[k] for k in TARGETS]);spl=np.load(ROOT/'ml'/(case+'_split.npz'));va=spl['validation'];te=spl['test'];best=None;score=float('inf')
        vx=x[va];vy=y[va]
        if (ROOT/'uniform_refined/complete.json').exists():
            extra=np.genfromtxt(ROOT/'uniform_refined'/(case+'.csv'),delimiter=',',names=True);es=np.load(ROOT/'uniform_refined'/(case+'_split.npz'))['validation']
            vx=np.concatenate([vx,features(extra)[es]]);vy=np.concatenate([vy,np.column_stack([extra[k] for k in TARGETS])[es]])
        for folder in sources:
            b=joblib.load(ROOT/folder/(case+'.joblib'));m=metrics(vy,b['model'].predict(vx));comparisons.append(dict(case=case,source=folder,method=b['method'],r2=m['r2'],median_error_percent=m['median_error_percent'],p95_error_percent=m['p95_error_percent']))
            if m['median_error_percent']<score:score=m['median_error_percent'];best=b
        bundles[case]=best;joblib.dump(best,models_dir/(case+'.joblib'));p=best['model'].predict(x[te]);model_metrics[case]=dict(method=best['method'],validation_median_percent=score,test=metrics(y[te],p))
        rows=[dict(row=int(idx),**{k:float(y[idx,j]) for j,k in enumerate(TARGETS)},**{'pred_'+k:float(p[i,j]) for j,k in enumerate(TARGETS)}) for i,idx in enumerate(te)];write_csv(out/(case+'_test_predictions.csv'),rows)
        fig,axs=plt.subplots(2,2,figsize=(9,8))
        for j,ax in enumerate(axs.flat):
            xx=abs(y[te,j]);yy=abs(p[:,j]);ax.scatter(xx,yy,s=4,alpha=.3);ax.set_xscale('log');ax.set_yscale('log');lo=max(min(xx.min(),yy.min()),1e-25);hi=max(xx.max(),yy.max());ax.plot([lo,hi],[lo,hi],'k--');ax.set_title(TARGETS[j]);ax.set_xlabel('SPICE magnitude (A)');ax.set_ylabel('Predicted magnitude (A)')
        fig.suptitle(case+' held-out test');fig.tight_layout();fig.savefig(out/(case+'_parity.png'),dpi=150);plt.close(fig)
        print('Selected',case,best['method'],'validation median',score,flush=True)
    write_csv(out/'selection_comparison.csv',comparisons);(out/'transistor_metrics.json').write_text(json.dumps(model_metrics,indent=2))
    baseline=list(csv.DictReader((ROOT/'ml/validation_comparison.csv').open()))
    # Four original algorithm families are reported from their common baseline
    # training/validation experiment. Later refinements have a separate table.
    for r in baseline:r['selected_variant']=r['method']
    write_csv(out/'four_method_comparison.csv',baseline)

    refs=json.loads((ROOT/'gates/reference.json').read_text());requests={c:[] for c in CASES};keys={c:[] for c in CASES}
    voltage_rows=[]
    for r in refs:
        for node,value in r['voltages'].items():
            voltage_rows.append(dict(gate=r['gate'],bits=r['bits'],corner=r['corner'],node=node,spice_voltage=value,ml_input_voltage=value,independently_predicted=False))
    write_csv(out/'gate_node_voltages.csv',voltage_rows)
    for r in refs:
        c=r['conditions'];v=r['voltages']
        for name,kind,d,g,s,b in devices(r['gate']):
            high=v[g]>c['vdd']/2;on=high if kind=='nmos' else not high;case=kind+('_on' if on else '_off');requests[case].append(dict(vdd=c['vdd'],temp=c['temp'],w=180e-9 if kind=='pmos' else 90e-9,vd=v[d],vs=v[s],**c[kind]));keys[case].append((r['gate'],r['bits'],r['corner'],name))
    cache={}
    for case in CASES:
        rows=requests[case];x=features({k:np.array([r[k] for r in rows]) for k in rows[0]});p=bundles[case]['model'].predict(x);cache.update(zip(keys[case],p));print('Predicted gate devices',case,len(rows),flush=True)
    bundles['_predictions']=cache;rows=[]
    for r in refs:
        total,supply=predict(r,bundles);rows.append(dict(gate=r['gate'],bits=r['bits'],corner=r['corner'],spice=r['spice_leakage'],ml=total,spice_vdd=r['spice_vdd_current'],ml_vdd=supply,output_voltage=r['voltages']['out']))
    write_csv(out/'gate_predictions.csv',rows);summary=[]
    for gate,bits in dict.fromkeys((r['gate'],r['bits']) for r in rows):
        sub=[r for r in rows if r['gate']==gate and r['bits']==bits];y=np.array([r['spice'] for r in sub]);p=np.array([r['ml'] for r in sub]);e=100*abs(p-y)/np.maximum(abs(y),1e-18)
        summary.append(dict(gate=gate,bits=bits,spice_median_A=float(np.median(y)),ml_median_A=float(np.median(p)),bias_A=float(np.mean(p-y)),median_error_percent=float(np.median(e)),mean_error_percent=float(np.mean(e)),p95_error_percent=float(np.percentile(e,95))))
    write_csv(out/'gate_metrics.csv',summary)
    vdd_summary=[]
    for gate,bits in dict.fromkeys((r['gate'],r['bits']) for r in rows):
        sub=[r for r in rows if r['gate']==gate and r['bits']==bits];yy=np.array([r['spice_vdd'] for r in sub]);pp=np.array([r['ml_vdd'] for r in sub]);ee=100*abs(pp-yy)/np.maximum(abs(yy),1e-18)
        vdd_summary.append(dict(gate=gate,bits=bits,spice_median_A=float(np.median(yy)),ml_median_A=float(np.median(pp)),bias_A=float(np.mean(pp-yy)),median_error_percent=float(np.median(ee)),mean_error_percent=float(np.mean(ee)),p95_error_percent=float(np.percentile(ee,95))))
    write_csv(out/'gate_metrics_vdd_only.csv',vdd_summary)
    y=np.array([r['spice'] for r in rows]);p=np.array([r['ml'] for r in rows]);e=100*abs(p-y)/np.maximum(abs(y),1e-18)
    overall=dict(gate_cases=len(rows),median_error_percent=float(np.median(e)),mean_error_percent=float(np.mean(e)),p95_error_percent=float(np.percentile(e,95)),nonpositive_predictions=int((p<=0).sum()),mean_error_at_most_one_percent=bool(np.mean(e)<=1))
    (out/'overall.json').write_text(json.dumps(overall,indent=2))
    fig,ax=plt.subplots(figsize=(7,6));positive=(y>0)&(p>0);ax.scatter(y[positive],p[positive],s=5,alpha=.3);ax.set_xscale('log');ax.set_yscale('log');lo=min(y[positive].min(),p[positive].min());hi=max(y.max(),p.max());ax.plot([lo,hi],[lo,hi],'k--');ax.set_xlabel('SPICE static current (A)');ax.set_ylabel('ML static current (A)');ax.set_title('Part B — all 3,600 gate cases');fig.tight_layout();fig.savefig(out/'gate_parity.png',dpi=160);plt.close(fig)
    (out/'complete.json').write_text(json.dumps(dict(completed=True,accuracy=overall),indent=2));print(json.dumps(overall),flush=True)

if __name__=='__main__':main()
