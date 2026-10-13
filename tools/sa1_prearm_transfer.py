"""先行IRQはSA-1への要求だけを送り、197行のIRQで従来の転送を行う。"""
from sa1_fixed_map import change


def pipeline(text,line):
    assert 180<=line<197
    text=change(text,'  lda #197\n  .else\n  lda #203\n',
        f'  lda #{line}\n  .else\n  lda #203\n')
    text=change(text,'pipe_vertical_irq:\n  .endif\n  rep #$30\n',
        'pipe_vertical_irq:\n  .endif\n  rep #$30\n  jsl pipe_prearm_irq\n  jcs pipe_irq_exit\n')
    request='''  .ifdef SA1_PIPELINE_IRQ
  lda #0
  sta f:$00311c
  .endif
  lda #1
  sta f:$00311e
  .ifdef SA1_PIPELINE_IRQ
  sep #$20
  lda #$80
  sta f:$002200
  rep #$20
  .endif
'''
    text=change(text,request,'  ; 要求は先行IRQで発行済み。grantをここで消さない。\n')
    text+='''
.segment "BSS"
.export pipe_prearm_phase
pipe_prearm_phase: .res 2
.segment "GSU"
.export pipe_prearm_irq: far, pipe_prearm_issued: far, pipe_prearm_transfer: far, pipe_prearm_late: far
pipe_prearm_irq:
  lda pipe_prearm_phase
  bne pipe_prearm_second
  ; mainのatomic区間で197行を過ぎていたら、このIRQで直接転送する。
  sep #$20
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  rep #$20
  and #255
  cmp #194
  bcs pipe_prearm_late_begin
  lda #197
  sta f:$004209
  jsr pipe_prearm_request
  lda #1
  sta pipe_prearm_phase
pipe_prearm_issued:
  sec
  rtl
pipe_prearm_late_begin:
  ; 197行を再設定する時間も必要。194..196行なら通常IRQ時刻まで待つ。
  sep #$20
pipe_prearm_wait_late:
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  cmp #197
  bcc pipe_prearm_wait_late
  rep #$20
  jsr pipe_prearm_request
pipe_prearm_late:
  clc
  rtl
pipe_prearm_request:
  lda #0
  sta f:$00311c
  lda #1
  sta f:$00311e
  sep #$20
  lda #$80
  sta f:$002200
  rep #$20
  rts
pipe_prearm_second:
  stz pipe_prearm_phase
  lda #'''+str(line)+'''
  sta f:$004209
pipe_prearm_transfer:
  clc
  rtl
.segment "CODE"
'''
    return text
