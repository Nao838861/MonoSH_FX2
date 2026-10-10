"""DMA開始を16bit STYで行い、各記述子のM幅切替を省く。"""
from sa1_sparse_direct import replace


def pipeline(text, contiguous=False):
    begin=text.index('pipe_fast_unroll_start:\n')
    end=text.index('pipe_fast_unroll_end:\n',begin)
    old='  sep #$20\n  lda #1\n  sta f:$00420b\n  rep #$20\n'
    block=text[begin:end]
    assert block.count(old)==1
    text=text[:begin]+block.replace(old,'  sty $0b\n')+text[end:]
    text=replace(text,'pipe_fast_gate:\n','pipe_fast_gate:\n  lda #$4200\n  tcd\n  ldy #$fe01\n')
    text=replace(text,'pipe_fast_unroll_end:\n  rtl','pipe_fast_unroll_end:\n  lda #0\n  tcd\n  rtl')
    size=24 if contiguous else 34
    text=replace(text,'=12*'+str(size), '=12*'+str(size-8))
    text=replace(text,'.min(I,12)*'+str(size),'.min(I,12)*'+str(size-8))
    return text
