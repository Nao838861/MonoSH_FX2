"""右端に32px以下だけ見えるnative行は、短いprefixだけIRAMへ複写する。"""


def helper(text):
    text=text.replace('.import __RIGHTJIT_LOAD__, __RIGHTJIT_SIZE__\n','')
    a=text.index('sa1_right_clip_draw:\n');b=text.index('rightChain=$80\n',a)
    # helper自身のIRAMロードを除く。native行の短い命令列のみ0500へ置く。
    text=text[:a]+'sa1_right_clip_draw:\n  jml right_entry\n'+text[b:]
    a=text.index('  jsl sa1_dma_try_begin\n',text.index('right_scanned:\n'))
    b=text.index('right_copy_cpu:\n',a)
    text=text[:a]+text[b:]
    text=text.replace('right_entry:\n','right_entry:\nright_narrow_entry:\n',1)
    text=text.replace('right_ready:\n','right_ready:\nright_narrow_ready:\n',1)
    return '.setcpu "65816"\n.export right_narrow_entry: far, right_narrow_ready: far\n'+text


def fast(text,scenery=False):
    text='.setcpu "65816"\n.import sa1_right_clip_draw: far\n'+text
    old='  jsl sa1_edge_prepare\n'
    assert text.count(old)==1
    gate='''  lda $c4
  beq right_narrow_unavailable
  lda $38
  cmp #224
  bcc right_narrow_unavailable
  cmp #256
  bcs right_narrow_unavailable
  jsl sa1_right_clip_draw
  sec
  rtl
right_narrow_unavailable:
'''
    if scenery:
        gate=gate.replace('  cmp #224\n','  cmp #248\n',1)
        gate=gate.replace('  jsl sa1_right_clip_draw\n','''  lda $3e
  beq right_narrow_scenery
  cmp #2
  beq right_narrow_scenery
  cmp #3
  beq right_narrow_scenery
  cmp #5
  bne right_narrow_unavailable
right_narrow_scenery:
  jsl sa1_right_clip_draw
''',1)
    return text.replace(old,old+gate,1)
