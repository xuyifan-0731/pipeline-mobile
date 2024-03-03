from .webarena_map import SYSTEM_PROMPT as WEBARENA_MAP_PROMPT
from .webarena_shopping import SYSTEM_PROMPT as WEBARENA_SHOPPING_PROMPT
from .webarena_gitlab import SYSTEM_PROMPT as WEBARENA_GITLAB_PROMPT
from .webarena_reddit import SYSTEM_PROMPT as WEBARENA_REDDIT_PROMPT
from .webarena_shopping_admin import SYSTEM_PROMPT as WEBARENA_SHOPPING_ADMIN_PROMPT
from .webarena_template import SYSTEM_PROMPT as WEBARENA_BASIC_PROMPT

system_templates = {
    "map": WEBARENA_MAP_PROMPT,
    "shopping": WEBARENA_SHOPPING_PROMPT,
    "gitlab": WEBARENA_GITLAB_PROMPT,
    "reddit": WEBARENA_REDDIT_PROMPT,
    "shopping_admin": WEBARENA_SHOPPING_ADMIN_PROMPT,
    "basic": WEBARENA_BASIC_PROMPT,
}