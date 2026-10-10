"""反転敵弾をnative code cacheへ接続する。"""


def transform(name, text):
    if name == 'renderer':
        text = '.import sa1_bullet_cache_prepare: far, sa1_bullet_cache_init: far\n' + text
        old = '  bit #$30\n  beq :+\nunsupported_hflip:\n  bra unsupported_hflip\n:\n'
        assert text.count(old) == 1
        text = text.replace(old, '', 1)
        text = text.replace('  stz $1e\n', '  stz $1e\n  jsl sa1_bullet_cache_init\n  lda #0\n', 1)
        text = text.replace('  sta $c2\n  lda f:$ff0001,x', '  sta $c2\n  jsl sa1_bullet_cache_prepare\n  bcs cache_rows_ready\n  lda f:$ff0001,x', 1)
        text = text.replace('  jsl sa1_try_fast\n', 'cache_rows_ready:\n  jsl sa1_try_fast\n', 1)
    elif name == 'dirty':
        from sa1_flip_bullets import transform as flip_transform
        text = flip_transform(name, text)
        text = text.replace('  jmp dirty_untrimmed\n', '  lda f:$430004,x\n  pha\n  lda f:$430006,x\n  and #255\n  tax\n  pla\n  jsl sa1_find_shape\n  stx $ba\n  jmp dirty_untrimmed\n', 1)
    elif name == 'fast':
        text = text.replace('  sta $2234\n  lda #$80\n  sta $2230', '  sta $2234\n  cmp #$40\n  bcc :+\n  cmp #$44\n  bcs :+\n  lda #$81\n  bra :++\n:\n  lda #$80\n:\n  sta $2230', 1)
    return text
