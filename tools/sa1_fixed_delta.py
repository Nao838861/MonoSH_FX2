"""透明タイルへの切替を共有mapの差分更新で行い、消去CHR転送を省く。"""
from sa1_fixed_map import change


def pipeline(text,build,dma=False):
    text=change(text,'p3Queue: .res 4','.export fdStorage\nfdStorage: .res 1472*8\np3Queue: .res 4')
    text=change(text,'pipe_initialized: .res 2','''.segment "COLORBSS"
fdMask: .res 2
fdCost: .res 2
.segment "BSS"
pipe_initialized: .res 2''')
    text=change(text,'pipe_collect_adaptive:\n','pipe_collect_adaptive:\n  jsl fd_collect\n')
    text=change(text,'  sta fx4_page\n  txa\n','  sta fx4_page\n  jsl fd_flip\n  txa\n')
    # The reservation applies to this transfer's future flip, not the old front.
    text=change(text,'pipe_reserve_flip:\n','''pipe_reserve_flip:
  phx
  ldx pipe_record_offset
  lda pipe_available
  sec
  sbc pipe_records+60,x
  bcs :+
  lda #0
:
  sta pipe_available
  plx
''')
    code=(build.parent.parent/'game/sa1/v001/fixed_delta_cpu.inc').read_text(encoding='utf-8')
    if dma:
        code='.import fd_show: far\n'+code
        code=change(code,'''  asl
  sta f:$004305
  lda f:$434660
  asl
  asl
  asl
  sta fdMask
  asl
  asl
  asl
  clc
  adc fdMask
  adc #300
  sta fdCost''','''  asl
  sta fdMask
  asl
  clc
  adc fdMask
  sta f:$004305
  lda f:$434662
  sta fdCost''')
        begin=code.index('  tay\n',code.index('fd_flip:\n'))
        end=code.index('fd_flip_full:\n',begin)
        code=code[:begin]+'''  tay
  txa
  .repeat 8
    lsr
  .endrepeat
  tax
  lda f:fd_bases,x
  tax
  lda #$1801
  sta f:$004300
  sep #$20
  lda #^fd_show
  sta f:$004304
  lda #$80
  sta f:$002115
  rep #$20
fd_flip_item:
  lda a:$0000,x
  sta f:$004305
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  lda a:$0002,x
  sta f:$004302
  lda a:$0004,x
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  txa
  clc
  adc #6
  tax
  dey
  bne fd_flip_item
  bra fd_flip_done
'''+code[end:]
    text+='\n'+code
    text+='\n.segment "CODE"\n'
    return text
