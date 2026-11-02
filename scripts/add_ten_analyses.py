"""Create ten real, image-only saved examples, without invented acquisition times."""
from pathlib import Path
import sys,csv,json,base64
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis import ROOT
import server
from collections import defaultdict

def main():
    rows=list(csv.DictReader((ROOT/'data/public/splits/test.csv').read_text().splitlines()))
    measured={r['sample_id']:r for r in csv.DictReader((ROOT/'reports/test_per_image.csv').read_text().splitlines())}
    groups=defaultdict(list)
    for r in rows:groups[r['sample_id'].split('_TILE')[0]].append(r)
    selected=[]
    while len(selected)<10:
        for key in sorted(groups):
            if groups[key] and len(selected)<10:selected.append(groups[key].pop(0))
    summaries=[]
    with server.db() as c:existing={name:json.loads(result) for name,result in c.execute('SELECT name,result FROM incidents')}
    for i,row in enumerate(selected,1):
        name=f'Analysis {i:02d} - {row["sample_id"]}'
        if name in existing:r=existing[name]
        else:
            r=server.save_incident({'name':name,'model':'trained','image_base64':base64.b64encode((ROOT/'data/public'/row['image_path']).read_bytes()).decode(),'notes':f'Real held-out SAR image {row["sample_id"]}. Dataset acquisition time and geographic bounds are not supplied in this manifest. Image-only analysis; no AIS or source-vessel attribution. Original reference mask: {row["mask_path"]}. Source: Garcia-INPE, CC BY 4.0.'})
        m=measured[row['sample_id']]
        summaries.append({'analysis':f'{i:02d}','sample_id':row['sample_id'],'incident_id':r['id'],'candidate_regions':len(r['regions']),'predicted_slick_percent':round(r['mask_fraction']*100,2),'iou_percent':round(float(m['iou'])*100,2),'precision_percent':round(float(m['precision'])*100,2),'recall_percent':round(float(m['recall'])*100,2)})
        assert r['observation'] is None and not r['sources'] and not r['candidates']
        for k in ('image','mask','overlay'):assert (server.RUNTIME/r['id']/(k+'.png')).exists()
    (ROOT/'reports/ten_analyses.json').write_text(json.dumps(summaries,indent=2))
    with (ROOT/'reports/ten_analyses.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=summaries[0].keys());w.writeheader();w.writerows(summaries)
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
