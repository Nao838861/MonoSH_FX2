"""透明map差分の画素照合と不採用になった速度比較を保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_fixed_delta'
CASES=(
 'movestress_detinput_captureburst_fixedmap_resident_v1_tracepalette',
 'movestress_detinput_captureburst_fixeddelta_v6_tracepalette',
 'movestress_detinput_fixeddeltadma_v2_tracepalette',
 'movestress_detinput_captureburst_fixeddeltadma_v3_tracepalette',
)


def main():
 DEST.mkdir(parents=True,exist_ok=True)
 reference=packets(CASES[0]);cases=[]
 for name in CASES:
  d=BUILD/name;s=json.loads((d/'summary.json').read_text())
  assert s['pixelMatchedPresents']>=120 and not (d/'failure.txt').exists()
  actual=packets(name);n=min(len(reference),len(actual));assert reference[:n]==actual[:n]
  e={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','romSha256',
   'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals')}
  e.update(scenario=name,logicMatchedGenerations=n,
   firstVisibleField=s['presentationTimes'][0]['visibleField'],
   maxSa1Ms=max(x['totalSa1Ms'] for x in s['sa1Jobs']))
  if (d/'map_delta.jsonl').exists():
   jobs=[json.loads(x) for x in (d/'map_delta.jsonl').read_text().splitlines()]
   e['fullMapTransfers']=sum(x['count']==65535 for x in jobs)
   e['mapUpdateMsTotal']=sum(x['ms'] for x in jobs)
  cases.append(e)
 failures=[]
 for suffix in ('fixeddelta_v1','fixeddelta_v2','fixeddelta_v3','fixeddelta_v4'):
  name='movestress_detinput_captureburst_'+suffix+'_tracepalette';d=BUILD/name
  failures.append(dict(scenario=name,performanceComparisonEligible=False,
   reason=(d/'failure.txt').read_text() if (d/'failure.txt').exists() else '画素不一致・present00002'))
 archive=DEST/'evidence.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  folders=(*CASES,'fixeddelta_v6_build','fixeddeltadma_v3_build',*(x['scenario'] for x in failures))
  for name in folders:
   for p in sorted((BUILD/name).iterdir()):
    if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 report=dict(cases=cases,excludedFailures=failures,goal60fpsAchieved=False,
  adopted=False,evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
 (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=report['evidenceSha256']))


if __name__=='__main__':main()
