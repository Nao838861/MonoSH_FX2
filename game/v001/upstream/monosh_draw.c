#include "monosh_draw.h"

MonoshDrawCommand monosh_draw_commands[MONOSH_DRAW_MAX];
unsigned char monosh_draw_count;

void monosh_draw_begin(void)
{
    monosh_draw_count = 0u;
}
