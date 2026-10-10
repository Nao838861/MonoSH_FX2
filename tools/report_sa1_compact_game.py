"""ゲーム状態を8KB窓へ収めた試験を、失敗も含めて保存する。"""
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'build/sa1_game'
DEST = ROOT/'game/sa1/v001/results/20261010_compact_game'
CASES = (
    'movestress_compactmemory_tracepalette',
    'movestress_compactmemory_zero_tracepalette',
    'movestress_compactgame_tracepalette',
    'movestress_compactgame_margin_tracepalette',
    'movestress_compactgame_cputable_tracepalette',
    'bossmovestress_compactgame_cputable_tracepalette',
    'bossmovestress_compactgame_wram_tracepalette',
    'movestress_compactgame_wram_tracepalette',
    'flipfixture_compactgame_wram_tracepalette',
    'movestress_compactgame_wai_tracepalette',
    'bossmovestress_compactgame_wai_tracepalette',
    'flipfixture_compactgame_wai_tracepalette',
)


def packets(name):
    raw=(BUILD/name/'packet_trace.bin').read_bytes()
    offset=0
    frames=[]
    while offset+8 <= len(raw):
        count=struct.unpack_from('<H',raw,offset+6)[0]
        end=offset+8+count*10
        if end>len(raw):break
        frames.append(raw[offset:end])
        offset=end
    return frames


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    results=[]
    reference=packets('movestress_compactmemory_zero_tracepalette')
    for name in CASES:
        folder=BUILD/name
        if not folder.exists():continue
        entry={'scenario':name}
        summary=folder/'summary.json'
        if summary.exists():
            data=json.loads(summary.read_text())
            for key in ('fields','logic','presents','pixelMatchedPresents','romSha256','goal60fpsAchieved','presentationFieldIntervals','stalledTailFields'):
                if key in data:entry[key]=data[key]
            if data.get('presentationTimes'):entry['firstVisibleField']=data['presentationTimes'][0]['visibleField']
            if data.get('sa1Jobs'):entry['maxSa1Ms']=max(j['totalSa1Ms'] for j in data['sa1Jobs'])
        failure=folder/'failure.txt'
        if failure.exists():entry['failure']=failure.read_text()
        expected=next(folder.glob('present*_expected.bin'),None)
        if expected is not None and 'pixelMatchedPresents' not in entry:
            entry.setdefault('failure','pixel reference mismatch: '+expected.name)
        entry['verifiedRun']='pixelMatchedPresents' in entry and 'failure' not in entry
        if name.startswith('movestress_compactgame') and not failure.exists():
            actual=packets(name)
            count=min(len(reference),len(actual))
            entry['logicComparedGenerations']=count
            entry['firstLogicMismatch']=next((i+1 for i in range(count) if reference[i]!=actual[i]),None)
            assert entry['firstLogicMismatch'] is None
        log=folder/'game_offload.jsonl'
        if log.exists():
            jobs=[json.loads(line) for line in log.read_text().splitlines()]
            if jobs:
                entry['gameJobs']=len(jobs)
                entry['meanGameMs']=sum(j['ms'] for j in jobs)/len(jobs)
                entry['maxGameMs']=max(j['ms'] for j in jobs)
        captured=folder/'captured_pixels_verified.json'
        if captured.exists():entry['capturedPixels']=json.loads(captured.read_text())
        results.append(entry)
    archive=DEST/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for entry in results:
            folder=BUILD/entry['scenario']
            for path in sorted(folder.iterdir()):
                if path.is_file() and path.suffix!='.rgb':out.write(path,f"{folder.name}/{path.name}")
        for name in ('manifest.json','compact_memory.json','game.cfg','game.lbl','MonoSHSA1_4bpp_game.sfc'):
            out.write(BUILD/name,'current_build/'+name)
    with zipfile.ZipFile(archive) as check:assert check.testzip() is None
    result={'cases':results,'evidenceSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'goal60fpsAchieved':False}
    (DEST/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(results),'archiveBytes':archive.stat().st_size,'sha256':result['evidenceSha256']}))


if __name__=='__main__':main()
