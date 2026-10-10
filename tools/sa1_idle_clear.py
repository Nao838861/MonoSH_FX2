"""共有raw面の所有権を公開し、描画待機中にだけ先行消去する。"""


def replace(text, old, new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def pipeline(text):
    text=replace(text,'  inc pipe_initialized\n','''  inc pipe_initialized
  ldx #12
  lda #0
ic_init_busy:
  sta f:$4307a0,x
  dex
  dex
  bpl ic_init_busy
''')
    text=replace(text,'  sta pipe_bw_busy,x\n','  sta pipe_bw_busy,x\n  sta f:$4307a0,x\n')
    return replace(text,'  stz pipe_bw_busy,x\n','  stz pipe_bw_busy,x\n  lda #0\n  sta f:$4307a0,x\n')


def renderer(text):
    text='.setcpu "65816"\n.import sa1_idle_clear: far\n'+text
    return replace(text,'wait_job:\n  jsl sa1_dma_poll\n','wait_job:\n  jsl sa1_idle_clear\n  jsl sa1_dma_poll\n')
