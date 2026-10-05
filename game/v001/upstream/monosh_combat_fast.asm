SECTION code_compiler

PUBLIC _monosh_combat_fast_update_bullets
PUBLIC _monosh_combat_fast_render
PUBLIC _monosh_combat_fast_frame
PUBLIC _monosh_combat_fast_render_cached
PUBLIC _monosh_combat_fast_cache_reset
PUBLIC _monosh_combat_reflect_bullet
PUBLIC _monosh_combat_build_collision_bands
PUBLIC _monosh_collision_band_bits
PUBLIC _monosh_collision_min_x
PUBLIC _monosh_collision_max_x

EXTERN _monosh_player_bullets
EXTERN _monosh_player_bullet_count
EXTERN _monosh_player_bullet_sizes
EXTERN _monosh_reflected_bullets
EXTERN _monosh_reflected_bullet_count
EXTERN _monosh_bullet_reflect_rng
EXTERN _mode3_attributes
EXTERN _mode3_attribute_count
EXTERN _monosh_combat_fire_cooldown
EXTERN _monosh_runtime_fire_actions
EXTERN _monosh_player_x
EXTERN _monosh_player_bottom
EXTERN _monosh_runtime_frame_counter
EXTERN _monosh_collision_bullet_bands

; Build the inverse eight-band player-shot broad phase as one bit set.  Exact
; projectile Z is checked after this reject, so consumers need only know
; whether their band is occupied.  A ROM row replaces up to fifteen range
; stores for the three live shots.
_monosh_combat_build_collision_bands:
    ld b,0
    ld a,255
    ld (_monosh_collision_min_x),a
    xor a
    ld (_monosh_collision_max_x),a
    ld a,(_monosh_player_bullets+0)
    cp 1
    jr nz,monosh_combat_collision_band_slot1
    ld a,(_monosh_player_bullets+1)
    ld (_monosh_collision_min_x),a
    ld (_monosh_collision_max_x),a
    ld a,(_monosh_player_bullets+3)
    cp 56
    jr nc,monosh_combat_collision_band_slot1
    ld e,a
    ld d,0
    ld hl,monosh_combat_collision_masks_by_wz
    add hl,de
    ld a,b
    or (hl)
    ld b,a
monosh_combat_collision_band_slot1:
    ld a,(_monosh_player_bullets+5)
    cp 1
    jr nz,monosh_combat_collision_band_slot2
    ld a,(_monosh_player_bullets+6)
    ld e,a
    ld a,(_monosh_collision_min_x)
    cp e
    jr c,monosh_combat_collision_band_slot1_min_ready
    ld a,e
    ld (_monosh_collision_min_x),a
monosh_combat_collision_band_slot1_min_ready:
    ld a,(_monosh_collision_max_x)
    cp e
    jr nc,monosh_combat_collision_band_slot1_max_ready
    ld a,e
    ld (_monosh_collision_max_x),a
monosh_combat_collision_band_slot1_max_ready:
    ld a,(_monosh_player_bullets+8)
    cp 56
    jr nc,monosh_combat_collision_band_slot2
    ld e,a
    ld d,0
    ld hl,monosh_combat_collision_masks_by_wz
    add hl,de
    ld a,b
    or (hl)
    ld b,a
monosh_combat_collision_band_slot2:
    ld a,(_monosh_player_bullets+10)
    cp 1
    jr nz,monosh_combat_collision_band_done
    ld a,(_monosh_player_bullets+11)
    ld e,a
    ld a,(_monosh_collision_min_x)
    cp e
    jr c,monosh_combat_collision_band_slot2_min_ready
    ld a,e
    ld (_monosh_collision_min_x),a
monosh_combat_collision_band_slot2_min_ready:
    ld a,(_monosh_collision_max_x)
    cp e
    jr nc,monosh_combat_collision_band_slot2_max_ready
    ld a,e
    ld (_monosh_collision_max_x),a
monosh_combat_collision_band_slot2_max_ready:
    ld a,(_monosh_player_bullets+13)
    cp 56
    jr nc,monosh_combat_collision_band_done
    ld e,a
    ld d,0
    ld hl,monosh_combat_collision_masks_by_wz
    add hl,de
    ld a,b
    or (hl)
    ld b,a
monosh_combat_collision_band_done:
    ld a,b
    ld (_monosh_collision_bullet_bands+0),a
    ret

_monosh_collision_band_bits:
    defb $01,$02,$04,$08,$10,$20,$40,$80
monosh_combat_collision_masks_by_wz:
    defb $07,$07,$07,$07,$07,$07,$07,$07
    defb $0f,$0f,$0f,$0f,$0f,$0f,$0f,$0f
    defb $1f,$1f,$1f,$1f,$1f,$1f,$1f,$1f
    defb $3e,$3e,$3e,$3e,$3e,$3e,$3e,$3e
    defb $7c,$7c,$7c,$7c,$7c,$7c,$7c,$7c
    defb $f8,$f8,$f8,$f8,$f8,$f8,$f8,$f8
    defb $f0,$f0,$f0,$f0,$f0,$f0,$f0,$f0

; Fastcall entry: L=source player-bullet index, H=reflecting object/part.
; The detached pool matches the source game's three reflected-shot slots,
; but its motion is edge-limited rather than lifetime-limited.
_monosh_combat_reflect_bullet:
    ld a,l
    cp 3
    ret nc
    ld (monosh_combat_reflect_source_index),a
    ld a,h
    ld (monosh_combat_reflect_object_index),a
    push ix
    ld a,(monosh_combat_reflect_source_index)
    ld l,a
    ld h,0
    ld e,l
    ld d,0
    add hl,hl
    add hl,hl
    add hl,de
    ld de,_monosh_player_bullets
    add hl,de
    push hl
    pop ix
    ld a,(ix+0)
    cp 1
    jp nz,monosh_combat_reflect_done
    ld (monosh_combat_reflect_source_pointer),ix
    ld a,(ix+1)
    ld (monosh_combat_reflect_source_x),a
    ld a,(ix+2)
    ld (monosh_combat_reflect_source_y),a

    ; rng += frame + bullet*2 + reflector*4 + 3, as in MonoSH.
    ld a,(monosh_combat_reflect_source_index)
    add a,a
    ld e,a
    ld a,(monosh_combat_reflect_object_index)
    add a,a
    add a,a
    add a,e
    ld e,a
    ld a,(_monosh_runtime_frame_counter)
    add a,e
    ld e,a
    ld a,(_monosh_bullet_reflect_rng)
    add a,e
    add a,3
    ld (_monosh_bullet_reflect_rng),a
    and 7
    ld (monosh_combat_reflect_velocity_index),a

    ld ix,_monosh_reflected_bullets
    ld b,3
monosh_combat_reflect_find_slot:
    ld a,(ix+0)
    or a
    jr z,monosh_combat_reflect_new_slot
    ld de,5
    add ix,de
    djnz monosh_combat_reflect_find_slot

    ; All occupied: n mod 3 == (high nibble + low nibble) mod 3.
    ld a,(_monosh_bullet_reflect_rng)
    and 15
    ld e,a
    ld a,(_monosh_bullet_reflect_rng)
    rrca
    rrca
    rrca
    rrca
    and 15
    add a,e
monosh_combat_reflect_mod3:
    cp 3
    jr c,monosh_combat_reflect_slot_index_ready
    sub 3
    jr monosh_combat_reflect_mod3
monosh_combat_reflect_slot_index_ready:
    ld l,a
    ld h,0
    ld e,l
    ld d,0
    add hl,hl
    add hl,hl
    add hl,de
    ld de,_monosh_reflected_bullets
    add hl,de
    push hl
    pop ix
    jr monosh_combat_reflect_have_slot

monosh_combat_reflect_new_slot:
    ld a,(_monosh_reflected_bullet_count)
    inc a
    ld (_monosh_reflected_bullet_count),a
monosh_combat_reflect_have_slot:
    ld a,1
    ld (ix+0),a
    ld a,(monosh_combat_reflect_source_x)
    ld (ix+1),a
    ld a,(monosh_combat_reflect_source_y)
    ld (ix+2),a
    ld a,(monosh_combat_reflect_velocity_index)
    ld e,a
    ld d,0
    ld hl,monosh_combat_reflect_velocity_x
    add hl,de
    ld a,(hl)
    ld (ix+3),a
    ld hl,monosh_combat_reflect_velocity_y
    add hl,de
    ld a,(hl)
    ld (ix+4),a

    ld ix,(monosh_combat_reflect_source_pointer)
    xor a
    ld (ix+0),a
    ld a,(_monosh_player_bullet_count)
    or a
    jr z,monosh_combat_reflect_done
    dec a
    ld (_monosh_player_bullet_count),a
monosh_combat_reflect_done:
    pop ix
    ret

; Complete per-field fire path.  Z is an immediate edge-triggered shot.
; Held X repeats once per four 60 Hz fields, matching the old 30 Hz auto-fire
; count of one request every other game update without slowing Z response.
_monosh_combat_fast_frame:
    ld a,(_monosh_runtime_fire_actions)
    bit 0,a
    jr nz,monosh_combat_fast_try_spawn
    bit 1,a
    jr z,monosh_combat_fast_auto_released
    ld a,(_monosh_combat_fire_cooldown)
    or a
    jr z,monosh_combat_fast_auto_fire
    dec a
    ld (_monosh_combat_fire_cooldown),a
    jr monosh_combat_fast_advance_phase

monosh_combat_fast_auto_fire:
    ; Three wait fields plus this request field gives a four-field period.
    ld a,3
    ld (_monosh_combat_fire_cooldown),a
    jr monosh_combat_fast_try_spawn

monosh_combat_fast_auto_released:
    ; A new X press must fire immediately instead of inheriting the old wait.
    xor a
    ld (_monosh_combat_fire_cooldown),a
    jr monosh_combat_fast_advance_phase

monosh_combat_fast_try_spawn:
    ld a,(_monosh_player_bullet_count)
    cp 3
    jr nc,monosh_combat_fast_advance_phase
    ; The pool is exactly three slots.  Select its fixed address directly and
    ; fill linearly through HL; this removes IX setup, displacement stores and
    ; the five-byte pointer loop from every fourth held-fire field.
    ld hl,_monosh_player_bullets
    ld a,(hl)
    or a
    jr z,monosh_combat_fast_spawn
    ld hl,_monosh_player_bullets+5
    ld a,(hl)
    or a
    jr z,monosh_combat_fast_spawn
    ld hl,_monosh_player_bullets+10
monosh_combat_fast_spawn:
    ; The X repeat delay starts on the request, so a full pool cannot turn
    ; slot availability into a faster-than-configured burst.
    ld (hl),1
    inc hl
    ld a,(_monosh_player_x)
    ld (hl),a
    inc hl
    ld a,(_monosh_player_bottom)
    sub 20
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld a,2
    ld (hl),a
    ld a,(_monosh_player_bullet_count)
    inc a
    ld (_monosh_player_bullet_count),a

monosh_combat_fast_advance_phase:
    ret

; Three packed records: active,x,y,wz,timer.
_monosh_combat_fast_update_bullets:
    push ix
    ld ix,_monosh_player_bullets
    ld b,3
monosh_combat_update_loop:
    ld a,(ix+0)
    or a
    jr z,monosh_combat_update_next
    ld a,(ix+4)
    inc a
    ld (ix+4),a
    ld a,(ix+3)
    add a,2
    ld (ix+3),a
    ld a,(ix+4)
    cp 25
    jr c,monosh_combat_update_next
    xor a
    ld (ix+0),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
monosh_combat_update_next:
    ld de,5
    add ix,de
    djnz monosh_combat_update_loop
    pop ix
    ret

_monosh_combat_fast_render:
    ; Runtime always emits the fixed two-plane player immediately before
    ; this routine.  Player shots therefore own the linear prefix beginning
    ; at record 2; avoid rebuilding 2*8 through generic count arithmetic.
    ld c,2
    ld hl,_mode3_attributes+16

    ; The pool has exactly three records.  Address them directly so the hot
    ; firing path pays neither IX displacement loads nor pointer/counter loop
    ; maintenance for every 60 Hz field.
    ld a,(_monosh_player_bullets+0)
    or a
    jr z,monosh_combat_render_slot1
    ; Update and encode in the same three-slot pass.  This removes a second
    ; complete projectile-array scan from every firing field.
    ld a,(_monosh_player_bullets+4)
    inc a
    ld e,a
    ld (_monosh_player_bullets+4),a
    ld a,(_monosh_player_bullets+3)
    add a,2
    ld (_monosh_player_bullets+3),a
    ld a,e
    cp 25
    jr c,monosh_combat_render_slot0_live
    xor a
    ld (_monosh_player_bullets+0),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    jr monosh_combat_render_slot1
monosh_combat_render_slot0_live:
    ld d,0
    push hl                       ; preserve sequential attribute cursor
    ld hl,_monosh_player_bullet_sizes
    add hl,de
    ld a,(hl)
    ld e,a                       ; E = scaled bullet size
    pop hl                       ; restore sequential attribute cursor
    ld a,(_monosh_player_bullets+2)
    sub e
    ld (hl),a                    ; Y = centre/belt line - size
    inc hl
    xor a
    ld (hl),a                    ; Y high, source size 16x16
    inc hl
    ld (hl),e                    ; MGY
    inc hl
    ld (hl),a                    ; palette/flags
    inc hl
    ld a,e
    srl a
    ld d,a
    ld a,(_monosh_player_bullets+1)
    sub d
    ld (hl),a                    ; X = centre - size/2
    inc hl
    xor a
    ld (hl),$10                 ; X high, pattern page 1
    inc hl
    ld (hl),e                    ; MGX
    inc hl
    ld (hl),$0f                  ; dedicated player-shot pattern (slot 47)
    inc hl
    inc c

monosh_combat_render_slot1:
    ld a,(_monosh_player_bullets+5)
    or a
    jr z,monosh_combat_render_slot2
    ld a,(_monosh_player_bullets+9)
    inc a
    ld e,a
    ld (_monosh_player_bullets+9),a
    ld a,(_monosh_player_bullets+8)
    add a,2
    ld (_monosh_player_bullets+8),a
    ld a,e
    cp 25
    jr c,monosh_combat_render_slot1_live
    xor a
    ld (_monosh_player_bullets+5),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    jr monosh_combat_render_slot2
monosh_combat_render_slot1_live:
    ld d,0
    push hl
    ld hl,_monosh_player_bullet_sizes
    add hl,de
    ld a,(hl)
    ld e,a
    pop hl
    ld a,(_monosh_player_bullets+7)
    sub e
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld (hl),a
    inc hl
    ld a,e
    srl a
    ld d,a
    ld a,(_monosh_player_bullets+6)
    sub d
    ld (hl),a
    inc hl
    ld (hl),$10
    inc hl
    ld (hl),e
    inc hl
    ld (hl),$0f
    inc hl
    inc c

monosh_combat_render_slot2:
    ld a,(_monosh_player_bullets+10)
    or a
    jr z,monosh_combat_render_done
    ld a,(_monosh_player_bullets+14)
    inc a
    ld e,a
    ld (_monosh_player_bullets+14),a
    ld a,(_monosh_player_bullets+13)
    add a,2
    ld (_monosh_player_bullets+13),a
    ld a,e
    cp 25
    jr c,monosh_combat_render_slot2_live
    xor a
    ld (_monosh_player_bullets+10),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    jr monosh_combat_render_done
monosh_combat_render_slot2_live:
    ld d,0
    push hl
    ld hl,_monosh_player_bullet_sizes
    add hl,de
    ld a,(hl)
    ld e,a
    pop hl
    ld a,(_monosh_player_bullets+12)
    sub e
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld (hl),a
    inc hl
    ld a,e
    srl a
    ld d,a
    ld a,(_monosh_player_bullets+11)
    sub d
    ld (hl),a
    inc hl
    ld (hl),$10
    inc hl
    ld (hl),e
    inc hl
    ld (hl),$0f
    inc hl
    inc c
monosh_combat_render_done:
    jp monosh_combat_render_reflected

monosh_combat_render_reflected:
    ld a,(_monosh_reflected_bullet_count)
    or a
    jp z,monosh_combat_render_all_done
    push ix
    ld ix,_monosh_reflected_bullets
    ld b,3
monosh_combat_reflected_loop:
    ld a,(ix+0)
    or a
    jp z,monosh_combat_reflected_next

    ; Signed X update with explicit overflow tests.  Zero and 255 remain
    ; visible; deletion happens only when the next centre crosses an edge.
    ld e,(ix+3)
    bit 7,e
    jr nz,monosh_combat_reflected_x_negative
    ld a,(ix+1)
    add a,e
    jr c,monosh_combat_reflected_remove
    ld (ix+1),a
    jr monosh_combat_reflected_y
monosh_combat_reflected_x_negative:
    ld a,e
    neg
    ld e,a
    ld a,(ix+1)
    cp e
    jr c,monosh_combat_reflected_remove
    sub e
    ld (ix+1),a

monosh_combat_reflected_y:
    ld e,(ix+4)
    bit 7,e
    jr nz,monosh_combat_reflected_y_negative
    ld a,(ix+2)
    add a,e
    jr c,monosh_combat_reflected_remove
    cp 212
    jr nc,monosh_combat_reflected_remove
    ld (ix+2),a
    jr monosh_combat_reflected_emit
monosh_combat_reflected_y_negative:
    ld a,e
    neg
    ld e,a
    ld a,(ix+2)
    cp e
    jr c,monosh_combat_reflected_remove
    sub e
    ld (ix+2),a

monosh_combat_reflected_emit:
    ld a,c
    cp 64
    jp nc,monosh_combat_reflected_next
    ld a,(ix+2)
    sub 6
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    ld (hl),a
    inc hl
    ld (hl),12
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld a,(ix+1)
    sub 6
    ld (hl),a
    inc hl
    ld a,0
    sbc a,0
    and 3
    or $10                       ; player-shot pattern lives on sprite page 1
    ld (hl),a
    inc hl
    ld (hl),12
    inc hl
    ld (hl),$0f
    inc hl
    inc c
    jr monosh_combat_reflected_next

monosh_combat_reflected_remove:
    xor a
    ld (ix+0),a
    ld a,(_monosh_reflected_bullet_count)
    dec a
    ld (_monosh_reflected_bullet_count),a
monosh_combat_reflected_next:
    ld de,5
    add ix,de
    dec b
    jp nz,monosh_combat_reflected_loop
    pop ix
monosh_combat_render_all_done:
    ld a,c
    ld (_mode3_attribute_count),a
    ret

_monosh_combat_fast_cache_reset:
    ret

; Bullets advance and change size on every 60 Hz field.  The cache entry
; point is retained for ABI compatibility, but always refreshes.
_monosh_combat_fast_render_cached:
    jp _monosh_combat_fast_render

monosh_combat_reflect_velocity_x:
    defb $f4,$f6,$f8,$fa,6,8,10,12
monosh_combat_reflect_velocity_y:
    defb $fc,$f8,$f6,4,$fa,8,2,$fe

SECTION bss_compiler
_monosh_collision_min_x: defs 1
_monosh_collision_max_x: defs 1
monosh_combat_reflect_source_index: defs 1
monosh_combat_reflect_object_index: defs 1
monosh_combat_reflect_velocity_index: defs 1
monosh_combat_reflect_source_pointer: defs 2
monosh_combat_reflect_source_x: defs 1
monosh_combat_reflect_source_y: defs 1
