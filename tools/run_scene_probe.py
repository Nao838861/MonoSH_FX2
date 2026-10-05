"""30体を奥から描くGSU連続実行を測る。ゲームのscene再現ではなく人工負荷。"""

import json
from pathlib import Path
import re
import subprocess

from PIL import Image

from run_probe import PROBE, BUILD, HZ, MESEN_EXE, build, framebuffer, source_image, prepare_runtime, lua


def command(width, index):
    height=160*width//128
    visible=(68*width+127)//128
    r=[0]*16
    r[1]=(index*37)%(257-visible)
    r[2]=192-height-(index%3)*4
    r[3]=128//width;r[4]=128*256//width
    r[5]=r[1];r[6]=height;r[9]=visible
    kernel='integer'
    if width==128:
        kernel='runs_copy';r[9]=width
    elif width==64:
        kernel='packed_half';r[9]=visible//2
    elif width==32:
        kernel='packed_quarter';r[9]=visible
    return dict(kernel=kernel,seed=0,regs=r,width=visible,full_width=width)


def preview(data,path):
    palette=((0,0,0,0),(24,32,48,255),(100,150,200,255),(240,240,240,255))
    im=Image.new('RGBA',(256,192))
    for y in range(192):
        for x in range(256):
            a=((x//8)*24+y//8)*16+(y%8)*2
            bit=7-x%8
            c=((data[a]>>bit)&1)|(((data[a+1]>>bit)&1)<<1)
            im.putpixel((x,y),palette[c])
    im.save(path)


def main():
    scenes={'mixed30':[8]*22+[32]*6+[64]+[128],
            'near_heavy30':[8]*19+[32]*8+[64]*2+[128]}
    results=[]
    rows=source_image('tree')
    mesen=prepare_runtime(MESEN_EXE)
    for name,widths in scenes.items():
        dest=BUILD/name;dest.mkdir(parents=True,exist_ok=True)
        commands=[command(w,i) for i,w in enumerate(widths)]
        text=(PROBE/'gsu.s').read_text(encoding='utf-8')
        text=re.sub(r'iwt r11,#(?:\$0000|0)\n(\s*)ldw \(r11\)',r'iwt r3,#0\n\1ldw (r3)',text)
        text=re.sub(r'(\w+_stop:)\n\s*stop\n\s*nop',r'\1\n  jmp r11\n  nop',text)
        # macro生成の終了部も同じ呼び出し規約へ変える。
        text=text.replace('stopname:\n  stop\n  nop','stopname:\n  jmp r11\n  nop')
        text+='\n.segment "GSU"\n.export scene_entry,scene_stop\nscene_entry:\n'
        text+='  iwt r11,#.loword(scene_after_clear)\n  iwt r15,#.loword(clear_entry)\n  nop\nscene_after_clear:\n'
        for i,cmd in enumerate(commands):
            for reg in (1,2,3,4,5,6,7,9,10):
                text+=f'  iwt r{reg},#{cmd["regs"][reg]}\n'
            text+=f'  iwt r11,#.loword(scene_after_{i})\n  iwt r15,#.loword({cmd["kernel"]}_entry)\n  nop\nscene_after_{i}:\n'
        text+='scene_stop:\n  stop\n  nop\n'
        asm=dest/'scene.s';asm.write_text(text,encoding='utf-8')
        rom,labels=build(dest,rows,asm)
        job=dict(name=name,kernel='scene',seed=165,regs=[0]*15+[labels['scene_entry']&65535])
        code=(PROBE/'measure.lua').read_text(encoding='utf-8')
        code=code.replace('JOBS',lua([job])).replace('LABELS',lua(labels)).replace('REPORT',lua((dest/'clocks.tsv').as_posix())).replace('OUTDIR',lua(dest.as_posix()))
        script=dest/'measure.lua';script.write_text(code,encoding='utf-8')
        run=subprocess.run([str(mesen),'--testRunner','--timeout=20','--doNotSaveSettings',str(rom),str(script)],cwd=mesen.parent,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (dest/'emulator.log').write_bytes(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError((dest/'clocks.tsv').read_text())
        expected=bytes(12288)
        for cmd in commands:expected=framebuffer(rows,cmd,expected)
        actual=(dest/(name+'.bin')).read_bytes()
        assert len(actual)==12288 and actual==expected,'GSU composite differs from reference'
        last=(dest/'clocks.tsv').read_text().splitlines()[-1].split('\t')
        assert last[2]=='true','guard corrupted'
        clocks=int(last[1])
        preview(actual,dest/'gsu_framebuffer.png')
        result=dict(scene=name,sprites=30,master_clocks=clocks,ms=clocks/HZ*1000,
                    includes='full 12KiB clear + geometry register setup + scaling + compositing + flush',
                    excludes='CPU game logic, packet upload, framebuffer DMA',
                    framebuffer_match=True,guard=True,widths=widths)
        results.append(result);print(result)
    (BUILD/'scene_results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
