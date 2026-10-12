"""採取済みの連続負荷区間で、隠れた画素を省ける楽観的上限を測る。"""
import argparse,json,struct
from pathlib import Path
import numpy as np
from test_sa1_probe import reference


def pixels(packed):
    p=np.frombuffer(packed,np.uint8).reshape(192,128)
    return np.stack((p&15,p>>4),axis=2).reshape(192,256)

def word_rows(mask,draw):
    # native wordの基準はspriteの左byte。画面x=0へ固定すると2pxずれる場合がある。
    assert draw[2]<=128, 'this probe excludes objects spanning both viewport edges'
    left=draw[0]-draw[2]//2;phase=(left//2*2)%4
    return np.roll(mask,-phase,axis=1).reshape(192,64,4).any(axis=2)


def analyze(directory):
    frames=[]
    for path in sorted(directory.glob('present*_meta.bin')):
        generation=int(path.name[7:12])
        if not 530<=generation<=570:continue
        raw=path.read_bytes();count=struct.unpack_from('<H',raw,6)[0]
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(count)]
        expected=pixels(reference(dict(draws=draws)))
        actual=pixels(path.with_name(path.name.replace('_meta.bin','_fb.bin')).read_bytes())
        assert np.array_equal(expected[expected!=0],actual[expected!=0])
        covered=np.zeros((192,256),dtype=bool);objects=[]
        for draw in reversed(draws):
            opaque=pixels(reference(dict(draws=[draw])))!=0
            visible=opaque&~covered
            active_words=word_rows(opaque,draw)
            visible_words=word_rows(visible,draw)
            objects.append(dict(asset=draw[4],width=draw[2],height=draw[3],
                pixels=int(opaque.sum()),hiddenPixels=int((opaque&covered).sum()),
                words=int(active_words.sum()),fullyHiddenWords=int((active_words&~visible_words).sum()),
                fullyHidden=bool(opaque.any() and not visible.any())))
            covered|=opaque
        frame=dict(generation=generation,objects=objects)
        for key in ('pixels','hiddenPixels','words','fullyHiddenWords'):
            frame[key]=sum(o[key] for o in objects)
        frames.append(frame)
    assert len(frames)==41
    totals={key:sum(f[key] for f in frames) for key in ('pixels','hiddenPixels','words','fullyHiddenWords')}
    return dict(source=str(directory),frames=frames,totals=totals,
        hiddenPixelFraction=totals['hiddenPixels']/totals['pixels'],
        hiddenWordFraction=totals['fullyHiddenWords']/totals['words'],
        costModel='optimal per-pixel front-to-back coverage; coverage generation/tests/extra blending excluded',
        gameIntegrated=False,goal60fpsAchieved=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=analyze(args.directory);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:result[k] for k in ('totals','hiddenPixelFraction','hiddenWordFraction')})
