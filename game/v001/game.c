#include "port.h"
#include "games.h"
#include "monosh_player.h"
#include "monosh_stage.h"
#include "monosh_enemy.h"
#include "monosh_boss.h"
#include "monosh_boss_data.h"
#include "monosh_combat.h"
#include "mode3_sprite.h"

FxDraw fx_draw[FX_DRAW_MAX];
unsigned char fx_draw_count;
unsigned int fx_packet_count;
FxCommand fx_packet[FX_DRAW_MAX];
unsigned char fx_ground_phase;
unsigned int fx_buttons;
unsigned char fx_input, fx_fire_actions;
unsigned char monosh_runtime_fire_actions;
unsigned int monosh_runtime_frame_counter;
unsigned int ground_irq_vblank_count;
unsigned char monosh_runtime_paused;
unsigned char monosh_ground_offset = 16;
signed char monosh_ground_screen_delta = -12;
unsigned char monosh_title_visible = 1;
unsigned int fx_far_u_acc, fx_far_d_acc;
unsigned char hit_pending;
unsigned int old_buttons;
extern const unsigned char fx_ground_camera[145];
extern const unsigned char fx_ground_depth_rows[5265];
extern unsigned char fx_ground_world_phase;
const unsigned char *monosh_ground_depth_pointer;
extern unsigned char boss_part_x[], boss_part_bottom[], boss_part_z[], boss_part_active[], boss_part_timer[];
extern signed char boss_render_camera_delta;

void monosh_title_draw(unsigned char visible) { monosh_title_visible = visible; }

#if 0
void fx_submit(int x, int bottom, unsigned char width, unsigned char height,
               unsigned char asset, unsigned char flags, unsigned char z,
               unsigned char priority)
{
    FxDraw *d;
    if (!width || !height || fx_draw_count == FX_DRAW_MAX) return;
    if (x + (width >> 1) < 0 || x - (width >> 1) >= 256 ||
        bottom <= 20 || bottom - height >= 212) return;
    d = &fx_draw[fx_draw_count++];
    d->x = x; d->bottom = bottom; d->width = width; d->height = height;
    d->asset = asset; d->flags = flags; d->z = z; d->priority = priority;
}

#endif
/* C参照版。実行経路はpacket.sの同じ計算を使用する。 */
#if 0
void fx_build_packet_reference(void)
{
    unsigned char i, j;
    FxDraw temp;
    fx_packet_count = 0;
    /* far-to-near。自機と自弾は元の固定優先を最後に描く。 */
    for (i = 1; i < fx_draw_count; ++i) {
        temp = fx_draw[i]; j = i;
        while (j && (fx_draw[j-1].priority > temp.priority ||
            (fx_draw[j-1].priority == temp.priority && fx_draw[j-1].z < temp.z))) {
            fx_draw[j] = fx_draw[j-1]; --j;
        }
        fx_draw[j] = temp;
    }
    for (i = 0; i < fx_draw_count; ++i) {
        FxDraw *d = &fx_draw[i];
        FxCommand *p;
        int x, y, w, h, skip_x = 0, skip_y = 0;
        unsigned int du, dv, u0;
        if ((d->flags & MODE3_BLEND_50) && (monosh_runtime_frame_counter & 1)) continue;
        x = d->x - (d->width >> 1); y = d->bottom - d->height - 20;
        w = d->width; h = d->height;
        du = fx_du_table[d->asset][d->width];
        dv = fx_dv_table[d->asset][d->height];
        if (x < 0) { skip_x = -x; w += x; x = 0; }
        if (y < 0) { skip_y = -y; h += y; y = 0; }
        if (x+w > 256) w = 256-x;
        if (y+h > 192) h = 192-y;
        if (w <= 0 || h <= 0) continue;
        u0 = skip_x * du;
        if (d->flags & MODE3_FLIP_X) {
            u0 = (fx_asset_width[d->asset] << 8) - 1 - u0;
            du = -du;
        }
        p = &fx_packet[fx_packet_count++];
        p->x = p->left = x; p->y = y; p->du = du;
        p->dv = (d->flags & MODE3_FLIP_Y) ? -dv : dv;
        p->v0 = (d->asset & 1) ? 0x8000u : 0;
        if (d->flags & MODE3_FLIP_Y) p->v0 += (fx_asset_height[d->asset]<<8)-1-skip_y*dv;
        else p->v0 += skip_y*dv;
        p->height = h; p->width = w; p->u0 = u0; p->bank = fx_asset_bank[d->asset];
    }
}

#endif
#ifdef FX_REFERENCE
void monosh_boss_render_only(void)
{
    unsigned char i = 9, z, asset, frame;
    signed char camera_shift = monosh_ground_screen_delta - boss_render_camera_delta;
    const unsigned char *g;
    boss_render_camera_delta = monosh_ground_screen_delta;
    while (i) {
        --i;
        if (!boss_part_active[i]) continue;
        if (camera_shift) {
            int bottom = (int)boss_part_bottom[i] + camera_shift;
            boss_part_bottom[i] = bottom < 0 ? 0 : (bottom > 255 ? 255 : bottom);
        }
        z = boss_part_z[i] > 110 ? 110 : boss_part_z[i];
        asset = boss_part_active[i] == 2 ? MONOSH_DRAW_BOM0 :
                (i == 0 ? MONOSH_DRAW_BOSS_FACE : MONOSH_DRAW_BOSS_BODY);
        g = asset == MONOSH_DRAW_BOM0 ? monosh_boss_bom_geometry :
            (i == 0 ? monosh_boss_face_geometry : monosh_boss_body_geometry);
        g += (unsigned int)z << 1;
        if (asset == MONOSH_DRAW_BOM0) {
            frame = ((112-boss_part_timer[i])/8)%6;
            if (frame > 3) frame = 6-frame;
            if (frame) asset = 38+frame;
        }
        fx_submit(boss_part_x[i], boss_part_bottom[i], g[0], g[1], asset, 0, z, 0);
    }
}
#endif

void fx_init(void)
{
    monosh_combat_init(); monosh_player_init(); monosh_stage_init();
    monosh_enemy_init(); monosh_boss_init();
    monosh_ground_depth_pointer = fx_ground_depth_rows + 16u*81;
}

#ifdef FX_REFERENCE
void fx_frame(void)
{
    unsigned char flags, target, world_active, stage_ready = 0, stage_hit;
    fx_read_input();
#ifndef FX_4BPP
    if ((fx_buttons & 0x2000) && !(old_buttons & 0x2000)) fx_toggle_color();
#endif
    if ((fx_buttons & 0x1000) && !(old_buttons & 0x1000)) monosh_runtime_paused ^= 1;
    fx_input = 0; fx_fire_actions = 0;
    if (fx_buttons & 0x0100) fx_input |= MOVE_RIGHT;
    if (fx_buttons & 0x0200) fx_input |= MOVE_LEFT;
    if (fx_buttons & 0x0400) fx_input |= MOVE_DOWN;
    if (fx_buttons & 0x0800) fx_input |= MOVE_UP;
    if ((fx_buttons & 0x4000) && !(old_buttons & 0x4000)) fx_fire_actions |= 1;
    if (fx_buttons & 0x0080) fx_fire_actions |= 2;
    old_buttons = fx_buttons;
    monosh_runtime_fire_actions = fx_fire_actions;
    if (monosh_runtime_paused) return;
    ++monosh_runtime_frame_counter; ++ground_irq_vblank_count;
    world_active = monosh_player_state == MONOSH_PLAYER_ALIVE;
    if (world_active && ++fx_ground_phase == 14) fx_ground_phase = 0;
    monosh_player_update(fx_input, hit_pending); hit_pending = 0;
    if (monosh_player_bottom <= 56) target = 0;
    else if (monosh_player_bottom >= 201) target = 64;
    else target = fx_ground_camera[monosh_player_bottom-56];
    if (monosh_ground_offset < target) ++monosh_ground_offset;
    else if (monosh_ground_offset > target) --monosh_ground_offset;
    monosh_ground_screen_delta = (signed char)monosh_ground_offset - 28;
    monosh_ground_depth_pointer = fx_ground_depth_rows + (unsigned int)monosh_ground_offset*81;
    flags = monosh_player_draw_flags();
    world_active = monosh_player_state == MONOSH_PLAYER_ALIVE;
    if (world_active) {
        fx_ground_world_phase = (fx_ground_world_phase + ((monosh_player_x-128)>>4)) & 127;
        fx_far_u_acc += (monosh_player_x-128)*2;
        fx_far_d_acc += (monosh_player_x-128)*4;
    }
    fx_draw_count = 0;
    if (world_active && !monosh_player_stumble) monosh_combat_fast_frame();
    monosh_combat_render();
    fx_submit(monosh_player_x, 201, 32, 8, 38, 0, 0, 0);
    if (world_active) {
        hit_pending = monosh_enemy_frame();
        if (monosh_boss_state == MONOSH_BOSS_STAGE) {
            stage_hit = monosh_stage_frame();
            if (!hit_pending) hit_pending = stage_hit;
            if (monosh_enemy_stage_complete() && !monosh_enemy_active_count() &&
                !monosh_enemy_bullet_count && monosh_stage_is_clear()) stage_ready = 1;
        }
        if (monosh_boss_state != MONOSH_BOSS_STAGE || stage_ready) {
            monosh_boss_frame(stage_ready, monosh_player_x, monosh_player_bottom);
            boss_render_camera_delta = monosh_ground_screen_delta;
            monosh_boss_prepare_render(); monosh_boss_render_only();
        }
    } else {
        monosh_enemy_render_only(); monosh_stage_render_only(); monosh_boss_render_only();
    }
    fx_submit(monosh_player_x, monosh_player_bottom, 32, 48,
              monosh_player_draw_asset(), flags, 0, 2);
    if (monosh_title_visible) fx_submit(132, 133, 88, 38, 42, 0, 0, 0);
    if (monosh_boss_state == MONOSH_BOSS_DONE && monosh_boss_should_restart()) {
        monosh_stage_init(); monosh_enemy_init(); monosh_boss_init(); hit_pending = 0;
    }
    fx_build_packet(); fx_build_ground();
}
#endif

void main(void)
{
    fx_init();
    fx_frame();
    for (;;) { fx_present(); }
}
