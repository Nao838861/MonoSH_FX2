; SA-1で占有maskの差分listを作り、本体の割り込みを短くする。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_sparse_map_prepare: far
.segment "GSU"
fdWord=$a0
fdMask=$a2
fdDiff=$a4
fdPos=$a6
fdOffset=$a8
fdCount=$aa
fdBits=$ac
sa1_sparse_map_prepare:
  rep #$30
  lda $0116
  cmp #2
  bcs fd_init_done
  ldx #94
  lda #0
fd_init:
  sta f:$434600,x
  dex
  dex
  bpl fd_init
fd_init_done:
  stz fdOffset
  lda #32
  sta fdPos
  lda #4
  sta fdWord
fd_word:
  ldx fdWord
  lda f:$432800,x
  sta fdMask
  eor f:$434600,x
  sta fdDiff
  lda fdMask
  sta f:$434600,x
  lda fdDiff
  bne fd_bits
  lda fdPos
  clc
  adc #16
  sta fdPos
  bra fd_next
fd_bits:
  lda #16
  sta fdBits
fd_bit:
  lsr fdMask
  bcc fd_hidden
  lda fdPos
  ora #$8000
  bra fd_test
fd_hidden:
  lda fdPos
fd_test:
  lsr fdDiff
  bcc fd_skip
  ldx fdOffset
  sta f:$434000,x
  inc fdOffset
  inc fdOffset
fd_skip:
  inc fdPos
  dec fdBits
  bne fd_bit
fd_next:
  inc fdWord
  inc fdWord
  lda fdWord
  cmp #96
  bcc fd_word
  lda fdOffset
  lsr
  cmp #41
  bcs fd_full
  sta f:$434660
  rtl
fd_full:
  lda #$ffff
  sta f:$434660
  lda #$2401
  sta fdPos
  lda #4
  sta fdWord
fd_full_word:
  ldx fdWord
  lda f:$434600,x
  sta fdMask
  ; output cursor follows the tile position, independent of the mask index.
  lda fdPos
  sec
  sbc #$2401
  asl
  tax
  lda #16
  sta fdBits
fd_full_bit:
  lsr fdMask
  bcc :+
  lda fdPos
  bra :++
:
  lda #$2400
:
  sta f:$434000,x
  inx
  inx
  inc fdPos
  dec fdBits
  bne fd_full_bit
  inc fdWord
  inc fdWord
  lda fdWord
  cmp #96
  bcc fd_full_word
  rtl
