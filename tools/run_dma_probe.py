"""192行の表示開始をHDMAで固定し、全画像DMAの書き込み損失を測る。"""

import json
import subprocess

from run_probe import PROBE, BUILD, HZ, MESEN_EXE, lua, build, prepare_runtime, source_image
from PIL import Image


def main():
    dest=BUILD/'dma';dest.mkdir(parents=True,exist_ok=True)
    rom,labels=build(dest,source_image('solid'))
    cases=[dict(name='normal224_full14k',height=224,bytes=14336,hdma=[127,15,97,15,1,128,0]),
           dict(name='target192_full12k',height=192,bytes=12288,hdma=[16,128,127,15,65,15,1,128,0]),
           dict(name='target192_10k',height=192,bytes=10240,hdma=[16,128,127,15,65,15,1,128,0])]
    script=(PROBE/'dma_measure.lua').read_text(encoding='utf-8')
    script=script.replace('JOBS',lua(cases)).replace('REPORT',lua((dest/'dma.tsv').as_posix())).replace('OUTDIR',lua(dest.as_posix()))
    path=dest/'measure.lua';path.write_text(script,encoding='utf-8')
    mesen=prepare_runtime(MESEN_EXE)
    run=subprocess.run([str(mesen),'--testRunner','--timeout=20','--doNotSaveSettings','--enableStdout',str(rom),str(path)],
                       cwd=mesen.parent,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (dest/'emulator.log').write_bytes(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError((dest/'dma.tsv').read_text())
    rows=[]
    for line in (dest/'dma.tsv').read_text().splitlines():
        name,clocks,start,end,valid,total=line.split('\t')
        row=dict(case=name,master_clocks=int(clocks),ms=int(clocks)/HZ*1000,
                 start_line=int(start),end_line=int(end),valid_bytes=int(valid),requested_bytes=int(total),
                 lost_bytes=int(total)-int(valid))
        rows.append(row);print(row)
        raw=(dest/(name+'.rgb')).read_bytes()
        Image.frombytes('RGB',(256,len(raw)//(256*3)),raw).save(dest/(name+'_ppu.png'))
    assert len(rows)==len(cases),'missing DMA result'
    assert rows[0]['lost_bytes']>0 and rows[1]['lost_bytes']>0,'expected full transfer overflow was not reproduced'
    assert rows[2]['lost_bytes']==0,'10KiB control transfer should fit'
    (dest/'results.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':main()
