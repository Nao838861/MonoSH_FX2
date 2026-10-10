"""256KiB BW-RAM内に7枚の24KiB画像と32KiBの共有領域を配置する。"""

# 先頭の1KiBは左端クリップの保護領域。CC変換の1KiB境界も満たす。
SLOTS = (0x0440, 0x0441, 0x0442, 0x8440, 0x8441, 0x8442, 0x8443)


def transform(name, text):
    for old, new in (("4360", "4320"), ("436740", "432740"),
                     ("436800", "432800"), ("436802", "432802"),
                     ("436880", "432880"), ("436900", "432900"),
                     ("436980", "432980"), ("437800", "433800"),
                     ("437802", "433802")):
        text = text.replace("$" + old, "$" + new)
    if name == 'occupancy':
        a = text.index('  sta f:$432000,x')
        b = text.index('  inx', a)
        text = text[:a] + ''.join(f'  sta f:${0x432000+i*96:06x},x\n' for i in range(7)) + '  lda #0\n' + ''.join(f'  sta f:${0x432002+i*96:06x},x\n' for i in range(7)) + text[b:]
        text = text.replace('cmp #3', 'cmp #7').replace('adc #$6000', 'adc #$2000')
        # g-7は消去対象、g-2は裏面VRAM更新の対象。
        text = text.replace('  jsr oc_address\n  sta ocTwo', '  lda ocIndex\n  clc\n  adc #5\n  cmp #7\n  bcc :+\n  sbc #7\n:\n  jsr oc_address\n  sta ocTwo')
    elif name == 'renderer':
        text = text.replace('sa1_clear_start:\n  stz $10', 'sa1_clear_start:\n  lda $019a\n  sta $10')
        text = text.replace('  adc $0120,x\n  sta bgdest', '  adc $0120,x\n  clc\n  adc $019a\n  sta bgdest')
        # rowbaseからtile番号を求める計算は、画像のベースを足す前に行う。
        text = text.replace('  sta destbase\n  bra bounds_ready', '  clc\n  adc $019a\n  sta destbase\n  lda rowbase\n  clc\n  adc $019a\n  sta rowbase\n  bra bounds_ready')
        text = text.replace('  jsl sa1_transfer_mask_prepare', '  jsl sa1_transfer_mask_prepare\n  jsl sa1_deep_rebase')
        text = '.setcpu "65816"\n.import sa1_deep_rebase: far\n' + text
        text = text.replace('clear_tile_row:\n', '  jmp clear_tile_row\n.segment "BOOT"\nclear_tile_row:\n', 1)
        text = text.replace('sa1_clear_done:\n', '  jmp sa1_clear_done\n.segment "SA1"\nsa1_clear_done:\n', 1)
    elif name == 'fast':
        text = text.replace('  adc $48\n  sta spriteBase', '  adc $48\n  clc\n  adc $019a\n  sta spriteBase')
    elif name == 'edge':
        text = text.replace('  adc edgeOffset\n  sta edgeFirst', '  adc edgeOffset\n  clc\n  adc $019a\n  sta edgeFirst')
        text = text.replace('beq edge_return', 'jeq edge_return')
    elif name == 'transfer_mask':
        text = text.replace('tm_first:\n', '.segment "GSU"\ntm_first:\n')
    elif name == 'background_cache':
        text = text.replace('  adc #$8000\n  sta bgSlot', '  adc #$4000\n  sta bgSlot')
        a = text.index('  lda #$40\n  sta bgOldBank', text.index('sa1_background_initialize:'))
        text = text[:a] + '''  lda #0
  sta $f4
bg_initialize_bank:
  ldx $f4
  lda f:deep_slots,x
  sta bgOldBank
  and #$8400
  sta bgSlot
  clc
  adc #$6000
  sta $f2
bg_initialize_block:
  jsl sa1_dma_begin
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda #1024
  sta $2238
  lda #$0300
  sta $2232
  lda bgSlot
  sta $2235
  sep #$20
  lda bgOldBank
  sta $2237
  rep #$20
  jsl sa1_dma_end
  lda bgSlot
  clc
  adc #1024
  sta bgSlot
  cmp $f2
  bcc bg_initialize_block
  inc $f4
  inc $f4
  lda $f4
  cmp #14
  bcc bg_initialize_bank
  rtl
deep_slots:
  .word $0440,$0441,$0442,$8440,$8441,$8442,$8443
'''
    return text


REBASE = '''.setcpu "65816"
.smart
.export sa1_deep_rebase: far
.segment "BOOT"
sa1_deep_rebase:
  rep #$30
  lda $011a
  beq deep_rebase_done
  sta $f0
  ldx #0
deep_rebase_loop:
  lda f:$430802,x
  clc
  adc $019a
  sta f:$430802,x
  txa
  clc
  adc #6
  tax
  dec $f0
  bne deep_rebase_loop
deep_rebase_done:
  rtl
'''
