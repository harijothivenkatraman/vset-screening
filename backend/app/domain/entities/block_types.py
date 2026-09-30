from typing import Any, Literal

BlockType = Literal[
    "para",
    "kv",
    "olist",
    "list",
    "table",
    "cards",
    "comparison",
    "unknown",
]

CALLOUT_TITLES: frozenset[str] = frozenset({
    "Current position",
    "Validation position",
    "Next validation milestone",
    "Competitive position",
    "Financing position",
    "Product & technology differentiation",
    "Current product maturity",
    "Market opportunity analyst view",
    "Team-market fit",
})
