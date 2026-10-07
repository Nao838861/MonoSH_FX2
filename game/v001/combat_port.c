/* monosh_combat_fast.asm の状態更新をCへ翻訳。3枠・周期・反射表を保存。 */
#include "port.h"
#include "games.h"
#include "monosh_combat.h"
#include "monosh_runtime.h"
#include "monosh_player.h"
extern unsigned char monosh_combat_fire_cooldown, monosh_bullet_reflect_rng;
extern const unsigned char monosh_player_bullet_sizes[];
void monosh_combat_fast_render(void);

void monosh_combat_fast_cache_reset(void) {}
void v9968_copy_to_vram_linear(unsigned long address,
                             const unsigned char *data, unsigned int size)
{ (void)address; (void)data; (void)size; }

#ifdef FX_REFERENCE
void monosh_combat_fast_frame(void)
{
    unsigned char i, fire = 0;
    if (fx_fire_actions & 1) fire = 1;
    else if (fx_fire_actions & 2) {
        if (monosh_combat_fire_cooldown) --monosh_combat_fire_cooldown;
        else { monosh_combat_fire_cooldown = 3; fire = 1; }
    } else monosh_combat_fire_cooldown = 0;
    if (!fire || monosh_player_bullet_count == 3) return;
    for (i = 0; i < 3; ++i) {
        MonoshPlayerBullet *b = &monosh_player_bullets[i];
        if (b->active) continue;
        b->active = 1; b->screen_x = monosh_player_x;
        b->screen_y = monosh_player_bottom - 20;
        b->wz = 0; b->timer = 2; ++monosh_player_bullet_count;
        break;
    }
}

void monosh_combat_fast_render(void)
{
    unsigned char i, size;
    for (i = 0; i < 3; ++i) {
        MonoshPlayerBullet *b = &monosh_player_bullets[i];
        if (!b->active) continue;
        if (monosh_player_state == MONOSH_PLAYER_ALIVE) {
            ++b->timer; b->wz += 2;
            if (b->timer >= 25) {
                b->active = 0; --monosh_player_bullet_count; continue;
            }
        }
        size = monosh_player_bullet_sizes[b->timer];
        fx_submit(b->screen_x, b->screen_y, size, size,
                  MONOSH_DRAW_PBULLET, 0, 0, 2);
    }
    for (i = 0; i < 3; ++i) {
        MonoshReflectedBullet *b = &monosh_reflected_bullets[i];
        int x, y;
        if (!b->active) continue;
        x = b->screen_x; y = b->screen_y;
        if (monosh_player_state == MONOSH_PLAYER_ALIVE) {
            x += b->velocity_x; y += b->velocity_y;
            if (x < 0 || x > 255 || y < 0 || y >= 212) {
                b->active = 0; --monosh_reflected_bullet_count; continue;
            }
            b->screen_x = x; b->screen_y = y;
        }
        fx_submit(x, y, 12, 12, MONOSH_DRAW_PBULLET, 64, 0, 2);
    }
}

#endif
void monosh_combat_fast_render_cached(void) { monosh_combat_fast_render(); }

void monosh_combat_reflect_bullet(unsigned int packed)
{
    static const signed char vx[8] = {-12,-10,-8,-6,6,8,10,12};
    static const signed char vy[8] = {-4,-8,-10,4,-6,8,2,-2};
    unsigned char i, index = packed, object = packed >> 8;
    MonoshPlayerBullet *b;
    MonoshReflectedBullet *r;
    if (index >= 3) return;
    b = &monosh_player_bullets[index];
    if (b->active != 1) return;
    monosh_bullet_reflect_rng += monosh_runtime_frame_counter + index*2 + object*4 + 3;
    for (i = 0; i < 3; ++i) if (!monosh_reflected_bullets[i].active) break;
    if (i == 3) i = monosh_bullet_reflect_rng % 3;
    else ++monosh_reflected_bullet_count;
    r = &monosh_reflected_bullets[i];
    r->active = 1; r->screen_x = b->screen_x; r->screen_y = b->screen_y;
    r->velocity_x = vx[monosh_bullet_reflect_rng & 7];
    r->velocity_y = vy[monosh_bullet_reflect_rng & 7];
    b->active = 0; --monosh_player_bullet_count;
}
