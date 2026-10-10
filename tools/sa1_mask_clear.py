"""raw七面ごとの占有maskを保持し、空の間隔を消去から除く。"""
from sa1_vram_four import change


def occupancy(text):
    return '.setcpu "65816"\n.import sa1_mask_history: far\n'+change(text,'  sta ocIndex\n','  sta ocIndex\n  jsl sa1_mask_history\n  lda ocIndex\n')


def renderer(text):
    begin=text.index('  .ifdef SA1_TILE_DMA\n',text.index('sa1_dirty_done:\n'))
    end=text.index('sa1_clear_done:\n',begin)
    return '.setcpu "65816"\n.import sa1_mask_clear: far\n'+text[:begin]+'  jsl sa1_mask_clear\n'+text[end:]


def idle(text):
    return change(text,'  jsl sa1_dma_end\nidle_clear_done:', '''  tya
  clc
  adc icHistory
  adc #$0300
  tax
  lda #0
  sta f:$430000,x
  sta f:$430002,x
  jsl sa1_dma_end
idle_clear_done:''')
