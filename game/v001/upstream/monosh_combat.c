#include <games.h>
#include "mode3_sprite.h"
#include "monosh_combat.h"
#include "monosh_draw.h"
#include "monosh_runtime.h"
#include "v9968.h"

#define BULLET_LIFETIME 24u
#define BULLET_Z_SPEED   2u

MonoshPlayerBullet monosh_player_bullets[MONOSH_PLAYER_BULLET_MAX];
unsigned char monosh_player_bullet_count;
MonoshReflectedBullet monosh_reflected_bullets[MONOSH_REFLECTED_BULLET_MAX];
unsigned char monosh_reflected_bullet_count;
unsigned char monosh_bullet_reflect_rng;
unsigned char monosh_collision_bullet_bands[8u];

const unsigned char monosh_player_bullet_sizes[BULLET_LIFETIME + 1u] = {
    0u, 6u, 12u, 12u, 12u, 11u, 10u, 10u, 10u, 9u,
    8u, 8u, 8u, 7u, 6u, 6u, 6u, 6u, 5u, 5u,
    5u, 5u, 4u, 4u, 4u
};
unsigned char monosh_combat_fire_cooldown;
unsigned char monosh_combat_half_frame;

void monosh_combat_fast_update_bullets(void);
void monosh_combat_fast_render(void);
void monosh_combat_fast_render_cached(void);
void monosh_combat_fast_cache_reset(void);

static unsigned char abs8(signed int value)
{
    return (unsigned char)(value < 0 ? -value : value);
}

static void upload_bullet_pattern(void)
{
    unsigned char y;
    unsigned char row[8];

    for (y = 0u; y != 16u; ++y) {
        unsigned char pair;
        for (pair = 0u; pair != 8u; ++pair) {
            unsigned char x0 = (unsigned char)(pair << 1);
            unsigned char x1 = (unsigned char)(x0 + 1u);
            unsigned char d0 = (unsigned char)(abs8((signed int)x0 - 7) +
                                                abs8((signed int)y - 7));
            unsigned char d1 = (unsigned char)(abs8((signed int)x1 - 7) +
                                                abs8((signed int)y - 7));
            unsigned char c0 = d0 <= 2u ? 15u : (d0 <= 5u ? 13u :
                                                (d0 <= 7u ? 7u : 0u));
            unsigned char c1 = d1 <= 2u ? 15u : (d1 <= 5u ? 13u :
                                                (d1 <= 7u ? 7u : 0u));
            row[pair] = (unsigned char)((c0 << 4) | c1);
        }
        /* Player shots use free slot 47: pattern $0f on mode-3 page 1. */
        v9968_copy_to_vram_linear(0x10078UL + ((unsigned long)y << 7),
                                  row, 8u);
    }
}

static void fire_bullet(signed int player_x, signed int player_bottom)
{
    unsigned char i;

    if (monosh_player_bullet_count == MONOSH_PLAYER_BULLET_MAX) return;
    for (i = 0u; i != MONOSH_PLAYER_BULLET_MAX; ++i) {
        MonoshPlayerBullet *bullet = &monosh_player_bullets[i];
        if (!bullet->active) {
            bullet->active = 1u;
            bullet->screen_x = (unsigned char)player_x;
            bullet->screen_y = (unsigned char)(player_bottom - 20);
            bullet->wz = 0u;
            bullet->timer = 2u;
            ++monosh_player_bullet_count;
            return;
        }
    }
}

void monosh_combat_init(void)
{
    unsigned char i;
    for (i = 0u; i != MONOSH_PLAYER_BULLET_MAX; ++i) {
        monosh_player_bullets[i].active = 0u;
    }
    for (i = 0u; i != MONOSH_REFLECTED_BULLET_MAX; ++i) {
        monosh_reflected_bullets[i].active = 0u;
    }
    monosh_player_bullet_count = 0u;
    monosh_reflected_bullet_count = 0u;
    monosh_bullet_reflect_rng = 0u;
    monosh_combat_fire_cooldown = 0u;
    /* Retained as an ABI/debug byte; projectile state now advances on every
       60 Hz field inside the ROM renderer. */
    monosh_combat_half_frame = 0u;
    monosh_combat_fast_cache_reset();
    upload_bullet_pattern();
}

#ifndef __ROM__
void monosh_combat_build_collision_bands(void)
{
    unsigned char i;
    unsigned char bit = 1u;

    for (i = 0u; i != 8u; ++i) monosh_collision_bullet_bands[i] = 0u;
    /* Collision retains MonoSH's 30 Hz game-update cadence.  All shots are
       checked together on that update; the intervening field is visual
       interpolation only. */
    if ((monosh_runtime_frame_counter & 1u) != 0u) return;
    for (i = 0u; i != MONOSH_PLAYER_BULLET_MAX; ++i, bit <<= 1) {
        const MonoshPlayerBullet *bullet = &monosh_player_bullets[i];
        unsigned char z2;
        unsigned char first;
        unsigned char last;
        if (bullet->active != 1u) continue;
        z2 = (unsigned char)(bullet->wz << 1);
        first = z2 > 32u ? (unsigned char)((z2 - 32u) >> 4) : 0u;
        last = (unsigned char)((z2 + 32u) >> 4);
        if (last > 7u) last = 7u;
        do {
            monosh_collision_bullet_bands[first] |= bit;
        } while (first++ != last);
    }
}
#endif

void monosh_combat_update(unsigned char input,
                          signed int player_x,
                          signed int player_bottom)
{
    unsigned char fire = (unsigned char)(input & MOVE_FIRE);

    if (!fire) {
        monosh_combat_fire_cooldown = 0u;
    } else if (monosh_combat_fire_cooldown == 0u) {
        fire_bullet(player_x, player_bottom);
        monosh_combat_fire_cooldown = 6u;
    } else {
        --monosh_combat_fire_cooldown;
    }
    monosh_combat_half_frame = 0u;
}

void monosh_combat_render(void)
{
#ifdef __ROM__
    monosh_combat_fast_render_cached();
#else
    monosh_combat_fast_render();
#endif
}
