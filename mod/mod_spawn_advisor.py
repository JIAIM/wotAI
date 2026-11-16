# -*- coding: utf-8 -*-
"""Spawn Advisor 1.0.0 — топ-3 стартовые позиции на миникарте.

Советы рисуются цветными векторными кольцами — тем же механизмом, которым
клиент рисует круги обзора и отрисовки вокруг своего танка
(значок VIEW_RANGE_CIRCLES + команды as_addDrawRange и т.п.).
Цвет — число 0xRRGGBB, радиус — в метрах игрового мира.
Ранг 1 — фиолетовый, 2 — бирюзовый, 3 — зелёный.

Каждый шаг в try/except: если что-то устроено иначе, мод ничего не ломает,
а пишет в game.log, что не получилось.

Код совместим с Python 2.7 (клиент WoT) и использует print() как функцию.
"""
from __future__ import print_function

import sys

VERSION = '1.0.0'
DEBUG = False          # True — писать в лог список модулей миникарты
TOGGLE_KEY = 'KEY_F9'  # клавиша вкл/выкл меток (имя из модуля Keys клиента)
SHOW_FOR_ARTY = False  # арте советы не помогают (lift 0,98), поэтому по умолчанию не показываем

# Цвета рангов 1, 2, 3 (0xRRGGBB): фиолетовый, бирюзовый, зелёный
RANK_COLORS = [0x9400D3, 0x40E0D0, 0x32CD32]
ALPHA = 100            # непрозрачность колец; у клиентских кругов 50

# Каждая метка — несколько концентрических колец (команда, радиус в метрах).
# У одного значка VIEW_RANGE_CIRCLES каждая команда рисует одно своё кольцо,
# поэтому берём разные команды — получается «толстая» точка.
RINGS = [
    ('as_addDrawRange', 30.0),
    ('as_addMaxViewRage', 22.0),
    ('as_addMinSpottingRange', 14.0),
]

PREFIX = '[SpawnAdvisor]'

# Заполняется скриптом сборки из recommendations.parquet:
# {"07_lakeville": {"1": [[x, z], ...], "2": [[x, z], ...]}, ...}
ADVICE = {}

_state = {'minimap': None, 'entries': [], 'visible': True}


def log(message):
    print('%s %s' % (PREFIX, message))


def dump_minimap_api():
    """Список загруженных модулей с 'minimap' в имени и классы в них — для отладки."""
    try:
        names = sorted(name for name in sys.modules.keys() if 'minimap' in name.lower())
        log('minimap modules: %d' % len(names))
        for name in names[:60]:
            module = sys.modules.get(name)
            if module is None:
                continue
            classes = [attr for attr in dir(module)
                       if type(getattr(module, attr, None)).__name__ in ('type', 'classobj')]
            log('  %s: %s' % (name, ', '.join(classes[:40])))
    except Exception as error:
        log('dump_minimap_api error: %r' % (error,))


def install_minimap_hook():
    """Перехватить создание миникарты, чтобы получить ссылку на её компонент."""
    try:
        from gui.Scaleform.daapi.view.battle.shared.minimap import component
        cls = component.MinimapComponent
        original = cls._populate

        def _populate(self, *args, **kwargs):
            original(self, *args, **kwargs)
            _state['minimap'] = self
            log('minimap captured: %s' % type(self).__name__)

        cls._populate = _populate
        log('minimap hook installed')
    except Exception as error:
        log('minimap hook error: %r' % (error,))


def add_markers(map_name, team, attempt=0):
    import BigWorld
    minimap = _state['minimap']
    if minimap is None:
        if attempt < 15:
            BigWorld.callback(1.0, lambda: add_markers(map_name, team, attempt + 1))
        else:
            log('minimap was not captured in 15 s')
        return

    points = ADVICE.get(map_name, {}).get(str(team), [])
    if not points:
        log('no advice for %s team %s' % (map_name, team))
        return

    try:
        bottom_left, upper_right = minimap.getBoundingBox()
        width = upper_right[0] - bottom_left[0]
        height = upper_right[1] - bottom_left[1]
        log('arena size %.0f x %.0f' % (width, height))
    except Exception as error:
        log('getBoundingBox error: %r' % (error,))
        return

    for rank, (x, z) in enumerate(points, start=1):
        try:
            draw_ring_marker(minimap, rank, float(x), float(z), width, height)
        except Exception as error:
            log('marker %d error: %r' % (rank, error))


def draw_ring_marker(minimap, rank, x, z, width, height):
    """Одна метка: значок кругов обзора в точке (x, z) + несколько цветных колец."""
    import Math
    from gui.Scaleform.daapi.view.battle.shared.minimap import settings
    matrix = Math.Matrix()
    matrix.setTranslate(Math.Vector3(x, 0.0, z))
    # как клиент для своих кругов: без поворота, чтобы кольца не крутились с картой
    props = settings.TRANSFORM_FLAG.DEFAULT ^ settings.TRANSFORM_FLAG.NO_ROTATION
    entry_id = minimap.addEntry(settings.ENTRY_SYMBOL_NAME.VIEW_RANGE_CIRCLES,
                                settings.CONTAINER_NAME.PERSONAL,
                                matrix=matrix, active=True, transformProps=props)
    if not entry_id:
        log('marker %d: addEntry returned %r' % (rank, entry_id))
        return
    _state['entries'].append(entry_id)
    # размер арены нужен Flash, чтобы перевести метры в пиксели миникарты
    minimap.invoke(entry_id, settings.VIEW_RANGE_CIRCLES_AS3_DESCR.AS_INIT_ARENA_SIZE, width, height)
    color = RANK_COLORS[(rank - 1) % len(RANK_COLORS)]
    for command, radius in RINGS:
        minimap.invoke(entry_id, command, color, ALPHA, radius)
    log('marker %d at (%.0f, %.0f): entry %r color %06X' % (rank, x, z, entry_id, color))


def set_markers_visible(visible):
    """Показать или спрятать все наши метки на миникарте."""
    minimap = _state['minimap']
    _state['visible'] = visible
    if minimap is None:
        return
    for entry_id in _state['entries']:
        try:
            minimap.setActive(entry_id, visible)
        except Exception as error:
            log('setActive error: %r' % (error,))
    log('markers %s' % ('on' if visible else 'off'))


def on_key_down(event):
    try:
        import Keys
        if event.key != getattr(Keys, TOGGLE_KEY):
            return
        if hasattr(event, 'isRepeatedEvent') and event.isRepeatedEvent():
            return                      # клавишу держат — не мигать
        if _state['entries']:
            set_markers_visible(not _state['visible'])
    except Exception as error:
        log('on_key_down error: %r' % (error,))


def player_is_arty(player):
    """True, если игрок на арте (тег SPG у машины). При любой ошибке — False: лучше показать, чем молча скрыть."""
    try:
        tags = player.vehicleTypeDescriptor.type.tags
    except Exception:
        try:
            tags = player.arena.vehicles[player.playerVehicleID]['vehicleType'].type.tags
        except Exception:
            return False
    return 'SPG' in tags


def on_avatar_ready():
    try:
        import BigWorld
        player = BigWorld.player()
        _state['entries'] = []          # новый бой — старые метки остались в прошлой миникарте
        _state['visible'] = True
        map_name = player.arena.arenaType.geometryName
        team = player.team
        log('battle: map=%s team=%s advice=%d points' % (
            map_name, team, len(ADVICE.get(map_name, {}).get(str(team), []))))
        if not SHOW_FOR_ARTY and player_is_arty(player):
            log('arty: advice hidden')
            return
        BigWorld.callback(2.0, lambda: add_markers(map_name, team))
        if DEBUG:
            BigWorld.callback(5.0, dump_minimap_api)
    except Exception as error:
        log('on_avatar_ready error: %r' % (error,))


try:
    from PlayerEvents import g_playerEvents
    g_playerEvents.onAvatarReady += on_avatar_ready
    install_minimap_hook()
    from gui import InputHandler
    InputHandler.g_instance.onKeyDown += on_key_down
    log('loaded %s, advice for %d maps, toggle key %s' % (VERSION, len(ADVICE), TOGGLE_KEY))
except Exception as error:
    log('load error: %r' % (error,))
