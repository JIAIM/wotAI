# -*- coding: utf-8 -*-
"""Spawn Advisor 0.3.2 — топ-3 стартовые позиции на миникарте.

Советы рисуются как пронумерованные точки (1, 2, 3) — тем же способом,
каким клиент рисует точки захвата: addEntry + invoke(setPointNumber) + invoke(setState). Каждый шаг в try/except:
если в этой версии клиента что-то устроено иначе, мод ничего не ломает,
а пишет в python.log, что не нашлось, и список модулей миникарты.

Код совместим с Python 2.7 (клиент WoT) и использует print() как функцию.
"""
from __future__ import print_function

import sys

VERSION = '0.3.2'
DEBUG = False          # True — писать в лог список модулей миникарты и значков
MARKER_SCALE = 0.5     # размер точки относительно стандартного значка точки захвата
GALLERY = True         # True — вместо советов нарисовать 12 разных значков сеткой (для выбора внешнего вида)
TOGGLE_KEY = 'KEY_F9'  # клавиша вкл/выкл точек (имя из модуля Keys клиента)

# Галерея: значок → место на сетке 4 × 3 (слева направо, сверху вниз), номера 1–12
GALLERY_SYMBOLS = ['ARTY_HIT_DOT_MARKER', 'ARTY_MARKER', 'ARTILLERY_ENTRY', 'ARTILLERY_YELLOW_ENTRY',
                   'ATTENTION_MARKER', 'DEAD_POINT', 'VIEW_POINT', 'MARK_POSITION',
                   'NAVIGATION_POINT_MARKER', 'SHOOTING_POINT_MARKER', 'FLAG_POINT_MARKER', 'DISCOVERED_ITEM_MARKER']
GALLERY_X = [-300.0, -100.0, 100.0, 300.0]
GALLERY_Z = [300.0, 0.0, -300.0]
PREFIX = '[SpawnAdvisor]'

# Заполняется скриптом сборки из recommendations.parquet:
# {"07_lakeville": {"1": [[x, z], ...], "2": [[x, z], ...]}, ...}
ADVICE = {}

SYMBOL_CANDIDATES = ['CONTROL_POINT', 'ALLY_TEAM_SPAWN']
CONTAINER_CANDIDATES = ['TEAM_POINTS', 'ICONS']

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


def pick_symbol_and_container():
    from gui.Scaleform.daapi.view.battle.shared.minimap import settings
    symbols = settings.ENTRY_SYMBOL_NAME
    containers = settings.CONTAINER_NAME
    if DEBUG:
        log('available symbols: %s' % ', '.join(a for a in dir(symbols) if not a.startswith('_')))
        log('available containers: %s' % ', '.join(a for a in dir(containers) if not a.startswith('_')))
    symbol = next((getattr(symbols, n) for n in SYMBOL_CANDIDATES if hasattr(symbols, n)), None)
    container = next((getattr(containers, n) for n in CONTAINER_CANDIDATES if hasattr(containers, n)), None)
    return symbol, container


def draw_gallery(minimap):
    """Рисует по одному значку каждого вида на сетке 4 × 3 и пишет в лог, какой где."""
    import Math
    from gui.Scaleform.daapi.view.battle.shared.minimap import settings
    symbols = settings.ENTRY_SYMBOL_NAME
    container = settings.CONTAINER_NAME.EQUIPMENTS
    for index, name in enumerate(GALLERY_SYMBOLS):
        row, col = divmod(index, len(GALLERY_X))
        x, z = GALLERY_X[col], GALLERY_Z[row]
        if not hasattr(symbols, name):
            log('gallery %2d %-24s нет в этой версии' % (index + 1, name))
            continue
        try:
            matrix = Math.Matrix()
            matrix.setTranslate(Math.Vector3(x, 0.0, z))
            entry_id = minimap.addEntry(getattr(symbols, name), container, matrix=matrix, active=True)
            if entry_id:
                _state['entries'].append(entry_id)
            log('gallery %2d %-24s ряд %d, колонка %d (x=%.0f, z=%.0f): entry %r' % (
                index + 1, name, row + 1, col + 1, x, z, entry_id))
        except Exception as error:
            log('gallery %2d %-24s ошибка %r' % (index + 1, name, error))


def add_markers(map_name, team, attempt=0):
    import BigWorld
    minimap = _state['minimap']
    if minimap is None:
        if attempt < 15:
            BigWorld.callback(1.0, lambda: add_markers(map_name, team, attempt + 1))
        else:
            log('minimap was not captured in 15 s')
        return

    if GALLERY:
        draw_gallery(minimap)
        return

    points = ADVICE.get(map_name, {}).get(str(team), [])
    if not points:
        log('no advice for %s team %s' % (map_name, team))
        return

    try:
        import Math
        from gui.Scaleform.genConsts.BATTLE_MINIMAP_CONSTS import BATTLE_MINIMAP_CONSTS as consts
        from gui.Scaleform.daapi.view.battle.shared.minimap import settings
        from gui.battle_control import minimap_utils
        symbol, container = pick_symbol_and_container()
        log('using symbol=%r container=%r' % (symbol, container))
        if symbol is None or container is None:
            log('component methods: %s' % ', '.join(a for a in dir(minimap) if 'ntry' in a))
            return
        for rank, (x, z) in enumerate(points, start=1):
            # как клиент делает для своих статичных меток: позиция + масштаб в одной матрице,
            # и флаг FULL, чтобы миникарта применила к значку и масштаб тоже
            matrix = minimap_utils.makePositionAndScaleMatrix(
                Math.Vector3(float(x), 0.0, float(z)), (MARKER_SCALE, 1.0, MARKER_SCALE))
            entry_id = minimap.addEntry(symbol, container, matrix=matrix, active=True,
                                        transformProps=settings.TRANSFORM_FLAG.FULL)
            if not entry_id:
                log('marker %d: addEntry returned %r' % (rank, entry_id))
                continue
            # как клиент делает для точек захвата: номер точки и обычное состояние
            _state['entries'].append(entry_id)
            minimap.invoke(entry_id, consts.SET_POINT_NUMBER, rank)
            minimap.invoke(entry_id, consts.SET_STATE, consts.STATE_DEFAULT)
            log('marker %d at (%.0f, %.0f): entry %r' % (rank, x, z, entry_id))
    except Exception as error:
        log('add_markers error: %r' % (error,))
        try:
            log('component methods: %s' % ', '.join(a for a in dir(minimap) if 'ntry' in a))
        except Exception:
            pass


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
