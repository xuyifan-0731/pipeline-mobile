import numpy as np

from enum import IntEnum
from itertools import chain
from .constants import (
    SPECIAL_KEYS, ASCII_CHARSET, FREQ_UNICODE_CHARSET
)

class ActionTypes(IntEnum):
    NONE = 0
    # mouse wheel and keyboard, universal across all action spaces
    SCROLL = 1
    KEY_PRESS = 2

    # low level mouse and keyboard actions
    MOUSE_CLICK = 3
    KEYBOARD_TYPE = 4
    MOUSE_HOVER = 5

    # mid level mouse and keyboard actions
    CLICK = 6
    TYPE = 7
    HOVER = 8

    # page level actions, universal across all action spaces
    PAGE_FOCUS = 9
    NEW_TAB = 10
    GO_BACK = 11
    GO_FORWARD = 12
    GOTO_URL = 13
    PAGE_CLOSE = 14

    # high-leval actions that playwright support
    CHECK = 15
    SELECT_OPTION = 16

    STOP = 17

    def __str__(self) -> str:
        return f"ACTION_TYPES.{self.name}"
    

_key2id: dict[str, int] = {
    key: i
    for i, key in enumerate(
        chain(SPECIAL_KEYS, ASCII_CHARSET, FREQ_UNICODE_CHARSET, ["\n"])
    )
}
_id2key: list[str] = sorted(_key2id, key=_key2id.get)  # type: ignore[arg-type]

def _keys2ids(keys: list[int | str] | str) -> list[int]:
    return list(
        map(
            lambda key: ActionCreator._key2id[str(key)]
            if isinstance(key, str)
            else int(key),
            keys,
        )
    )
def __init__():
    pass


def create_none_action():
    return {
        "action_type": ActionTypes.NONE,
        "coords": np.zeros(2, dtype=np.float32),
        "element_role": 0,
        "element_name": "",
        "text": [],
        "page_number": 0,
        "url": "",
        "nth": 0,
        "pw_code": "",  # str that requires further processing
        "element_id": "",
        "key_comb": "",
        "direction": "",
        "answer": "",
        "raw_prediction": "",
        "label": "",
        "flag": False,
        "use_coords": False,
    }


def create_stop_action(
    answer: str
):
    action = create_none_action()
    action.update({
        "action_type": ActionTypes.STOP,
        "answer": answer
    })
    return action

 
def create_goto_url_action(
    url: str,
):
    action = create_none_action()
    action.update({
        "action_type": ActionTypes.GOTO_URL,
        "url": url,
    })
    return action


def create_type_action(
    text: str,
    left: float,
    top: float,
    flag: bool = True,
):
    action = create_none_action()
    action.update(
        {
            "action_type": ActionTypes.TYPE,
            "coords": np.array([left, top], dtype=np.float32),
            "text": _keys2ids(text),
            "flag": flag,
            "use_coords": True,
        }
    )
    return action


def create_click_action(
    left: float | None = None,
    top: float | None = None,
    is_right_click: bool = False,
):
    action = create_none_action()
    if left and top:
        action.update({
            "action_type": ActionTypes.MOUSE_CLICK,
            "coords": np.array([left, top], dtype=np.float32),
            "flag": is_right_click,
        })
    elif (not left) and (not top):
        action.update({
            "action_type": ActionTypes.CLICK,
            "flag": is_right_click,
        })
    else:
        raise ValueError("left and top must be both None or both not None")
    return action


def create_hover_action(
    left: float | None = None,
    top: float | None = None
):
    action = create_none_action()
    action.update({
        "action_type": ActionTypes.MOUSE_HOVER,
        "coords": np.array([left, top], dtype=np.float32),
    })
    return action


def create_key_press_action(
    key_comb: str
):
    def map_keys(key_comb: str) -> str:
        keys = key_comb.split("+")
        mapped_keys = []
        for key in keys:
            mapped_key = SPECIAL_KEY_MAPPINGS.get(key.lower(), key)
            mapped_keys.append(mapped_key)
        return "+".join(mapped_keys)

    action = create_none_action()
    mapped_key_comb = map_keys(key_comb)
    action.update({
        "action_type": ActionTypes.KEY_PRESS,
        "key_comb": mapped_key_comb,
    })
    return action

def create_scroll_action(
    direction: str
):
    assert direction in ["up", "down"]
    action = create_none_action()
    action.update({
        "action_type": ActionTypes.SCROLL,
        "direction": direction,
    })
    return action