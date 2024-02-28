ASCII_CHARSET = "".join(chr(x) for x in range(32, 128))
FREQ_UNICODE_CHARSET = "".join(chr(x) for x in range(129, 110000))
UTTERANCE_MAX_LENGTH = 8192
ATTRIBUTE_MAX_LENGTH = 256
TEXT_MAX_LENGTH = 256
TYPING_MAX_LENGTH = 64
URL_MAX_LENGTH = 256
MAX_ELEMENT_INDEX_IN_VIEWPORT = 10
MAX_ELEMENT_ID = 1000
MAX_ANSWER_LENGTH = 512

MIN_REF = -1000000
MAX_REF = 1000000

WINDOW_WIDTH = 500
WINDOW_HEIGHT = 240
TASK_WIDTH = 160
TASK_HEIGHT = 210

FLIGHT_WINDOW_WIDTH = 600
FLIGHT_WINDOW_HEIGHT = 700
FLIGHT_TASK_WIDTH = 375
FLIGHT_TASK_HEIGHT = 667
MAX_PAGE_NUMBER = 10

SPECIAL_KEYS = (
    "Enter",
    "Tab",
    "Control",
    "Shift",
    "Meta",
    "Backspace",
    "Delete",
    "Escape",
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "PageDown",
    "PageUp",
    "Meta+a",
)

SPECIAL_KEY_MAPPINGS = {
    "backquote": "Backquote",
    "minus": "Minus",
    "equal": "Equal",
    "backslash": "Backslash",
    "backspace": "Backspace",
    "meta": "Meta",
    "tab": "Tab",
    "delete": "Delete",
    "escape": "Escape",
    "arrowdown": "ArrowDown",
    "end": "End",
    "enter": "Enter",
    "home": "Home",
    "insert": "Insert",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
    "f11": "F11",
    "f12": "F12",
}