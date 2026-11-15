"""Reproducible Part A SPICE data. Run with Ubuntu Python, from any directory."""
from pathlib import Path
import argparse, concurrent.futures, csv, hashlib, json, os, re, subprocess, tempfile, time
import numpy as np

ROOT = Path(__file__).resolve().parent
PARAMS = ['vth0', 'toxe', 'ndep', 'u0', 'xj']
CASES = ['nmos_on', 'nmos_off', 'pmos_on', 'pmos_off']
COLS = ['vdd','temp','w','vd','vs','vg','vb'] + PARAMS + ['id','ig','is','ib']
SOURCE = (ROOT/'models/45nm_MGK.pm').read_text()
BLOCKS = {k: re.search(r'(?ims)^\.model\s+'+k+r'\b.*?(?=^\.model|\Z)', SOURCE).group() for k in ['nmos','pmos']}

def nominal(kind):
    return {p: float(re.search(r'\b'+p+r'\s*=\s*([^\s]+)', BLOCKS[kind], re.I).group(1)) for p in PARAMS}

def simulate(job):
    case, row = job
    kind = case.split('_')[0]
    block = BLOCKS[kind]
    for p in PARAMS:
        block = re.sub(r'(\b'+p+r'\s*=\s*)[^\s]+', lambda m: m[1]+format(row[p],'.17g'), block, flags=re.I)
    deck = '* Independently sampled transistor\n'+block+'\n'
    deck += '.options gmin=1e-18 abstol=1e-18 reltol=1e-6 vntol=1e-9\n'
    deck += f'.temp {row["temp"]:.17g}\nM1 d g s b {kind} L=45n W={row["w"]:.17g}\n'
    for t in 'dgsb':
        deck += f'V{t} {t} 0 {row["v"+t]:.17g}\n'
    deck += '.control\nset numdgt=17\nop\nprint i(vd) i(vg) i(vs) i(vb)\nquit\n.endc\n.end\n'
    with tempfile.TemporaryDirectory(prefix='triode_') as td:
        p=Path(td)/'sample.cir'; p.write_text(deck)
        result=subprocess.run(['ngspice','-b',str(p)],capture_output=True,text=True,timeout=20)
    log=result.stdout+result.stderr
    if result.returncode or re.search(r'(?im)^\s*(fatal|error)',log):
        raise RuntimeError(log[-2500:])
    for t in 'dgsb':
        match=re.search(r'i\(v'+t+r'\)\s*=\s*([-+0-9.eE]+)',log,re.I)
        if not match: raise RuntimeError('Missing current: '+log[-2500:])
        row['i'+t]=-float(match[1])
    if not all(np.isfinite(row[k]) for k in COLS): raise RuntimeError('Nonfinite sample')
    return row

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--samples',type=int,default=10000); ap.add_argument('--workers',type=int,default=6); ap.add_argument('--output',default='data'); args=ap.parse_args()
    out=ROOT/args.output; out.mkdir(exist_ok=True)
    start=time.time(); summary={}
    for ci,case in enumerate(CASES):
        rng=np.random.default_rng(20261109+ci); kind=case.split('_')[0]; nom=nominal(kind); jobs=[]
        for i in range(args.samples):
            vdd=rng.uniform(.9,1.1)
            row=dict(vdd=vdd,temp=rng.uniform(-40,125),w=rng.uniform(45e-9,360e-9),vd=rng.uniform(0,vdd),vs=rng.uniform(0,vdd))
            row['vg']=vdd if case in ['nmos_on','pmos_off'] else 0.
            row['vb']=vdd if kind=='pmos' else 0.
            row.update({p:nom[p]*rng.uniform(.9,1.1) for p in PARAMS})
            jobs.append((case,row))
        rows=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(simulate,jobs):
                rows.append(row)
                if len(rows)%1000==0: print(case,len(rows), 'elapsed',round(time.time()-start,1),flush=True)
        with (out/(case+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=COLS); writer.writeheader(); writer.writerows(rows)
        currents=np.array([[r['i'+t] for t in 'dgsb'] for r in rows]); residual=abs(currents.sum(axis=1)); scale=abs(currents).sum(axis=1)
        summary[case]={'rows':len(rows),'max_kcl_abs_A':float(residual.max()),'max_kcl_relative':float((residual/np.maximum(scale,1e-30)).max()),'nominal_parameters':nom}
        print(case,summary[case],flush=True)
    summary.update(seconds=time.time()-start,model_sha256=hashlib.sha256((ROOT/'models/45nm_MGK.pm').read_bytes()).hexdigest(),seed_base=20261109,warning='Supplied oxide parameters retained: ngspice may ignore inconsistent dtox when toxe and toxp are both supplied. Only specified five parameters varied.')
    (out/'generation_summary.json').write_text(json.dumps(summary,indent=2))

if __name__=='__main__': main()
