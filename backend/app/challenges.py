"""Original problem wording and deterministic, versioned test fixtures.

Hidden cases are omitted from challenge browsing; this local review tool reveals
failure details AFTER an evaluation. They are not secret assessment material.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Case:
    name: str
    input: dict[str, Any]
    expected: Any
    hidden: bool = False


@dataclass(frozen=True)
class Challenge:
    id: str
    title: str
    category: str
    description: str
    specification: str
    constraints: str
    complexity: str
    reference: str
    buggy: str
    cases: tuple[Case, ...]

    def public(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "specification": self.specification,
            "constraints": self.constraints,
            "complexity": self.complexity,
            "reference": self.reference,
            "buggy": self.buggy,
            "test_count": len(self.cases),
            "examples": [
                {"input": c.input, "expected": c.expected} for c in self.cases if not c.hidden
            ],
        }


CHALLENGES = [
    Challenge(
        "two-sum",
        "Two Sum",
        "Algorithms",
        "Find the first pair discovered while scanning a list from left to right whose sum is the target.",
        "solve(nums: list[int], target: int) -> list[int]. Return [earlier_index, current_index], or []. Keep the first index of a repeated value; never reuse an index.",
        "0 <= len(nums) <= 10,000; integer values and target in [-10^6, 10^6].",
        "Reference: O(n) time and O(n) space.",
        "def solve(nums, target):\n    seen = {}\n    for i, value in enumerate(nums):\n        if target - value in seen:\n            return [seen[target - value], i]\n        seen.setdefault(value, i)\n    return []\n",
        "def solve(nums, target):\n    seen = {}\n    for i, value in enumerate(nums):\n        seen[value] = i\n        if target - value in seen:\n            return [seen[target - value], i]\n    return []\n",
        (
            Case("basic", {"nums": [2, 7, 11], "target": 9}, [0, 1]),
            Case("no-reuse", {"nums": [3], "target": 6}, [], True),
            Case("repeated", {"nums": [3, 3], "target": 6}, [0, 1], True),
            Case("empty", {"nums": [], "target": 0}, [], True),
            Case("negative", {"nums": [-4, 2, 5], "target": 1}, [0, 2], True),
        ),
    ),
    Challenge(
        "binary-search",
        "Binary Search",
        "Algorithms",
        "Locate the first occurrence of a target in an ascending integer list.",
        "solve(nums: list[int], target: int) -> int. Return the lowest matching index, otherwise -1.",
        "Sorted list, length 0..10,000; duplicates allowed.",
        "Reference: O(log n) time, O(1) space.",
        "def solve(nums, target):\n    left, right = 0, len(nums)\n    while left < right:\n        mid = (left + right) // 2\n        if nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid\n    return left if left < len(nums) and nums[left] == target else -1\n",
        "def solve(nums, target):\n    left, right = 0, len(nums) - 1\n    while left < right:\n        mid = (left + right) // 2\n        if nums[mid] == target:\n            return mid\n        if nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n",
        (
            Case("middle", {"nums": [1, 3, 5], "target": 3}, 1),
            Case("single", {"nums": [7], "target": 7}, 0, True),
            Case("duplicates", {"nums": [2, 2, 2, 2], "target": 2}, 0, True),
            Case("empty", {"nums": [], "target": 9}, -1, True),
            Case("absent", {"nums": [1, 3, 5], "target": 4}, -1, True),
        ),
    ),
    Challenge(
        "valid-parentheses",
        "Valid Parentheses",
        "Algorithms",
        "Check whether a bracket-only string is correctly nested and fully closed.",
        "solve(text: str) -> bool. Recognize (), [] and {}. Any other character makes the string invalid; the empty string is valid.",
        "Length 0..10,000.",
        "Reference: O(n) time, O(n) space.",
        'def solve(text):\n    stack = []\n    pairs = {")": "(", "]": "[", "}": "{"}\n    for ch in text:\n        if ch in "([{":\n            stack.append(ch)\n        elif ch in pairs and stack and stack[-1] == pairs[ch]:\n            stack.pop()\n        else:\n            return False\n    return not stack\n',
        'def solve(text):\n    return text.count("(") == text.count(")") and text.count("[") == text.count("]") and text.count("{") == text.count("}")\n',
        (
            Case("nested", {"text": "([]){}"}, True),
            Case("crossed", {"text": "([)]"}, False, True),
            Case("empty", {"text": ""}, True, True),
            Case("letters", {"text": "abc"}, False, True),
            Case("open", {"text": "(("}, False, True),
        ),
    ),
    Challenge(
        "merge-intervals",
        "Merge Intervals",
        "Algorithms",
        "Combine overlapping or touching closed intervals and return them sorted by start.",
        "solve(intervals: list[list[int]]) -> list[list[int]]. Each item is [start, end]. Do not modify the input.",
        "0..5,000 intervals; integer endpoints with start <= end.",
        "Reference: O(n log n) time, O(n) space.",
        "def solve(intervals):\n    merged = []\n    for start, end in sorted(intervals):\n        if merged and start <= merged[-1][1]:\n            merged[-1][1] = max(end, merged[-1][1])\n        else:\n            merged.append([start, end])\n    return merged\n",
        "def solve(intervals):\n    merged = []\n    for start, end in sorted(intervals):\n        if merged and start < merged[-1][1]:\n            merged[-1][1] = end\n        else:\n            merged.append([start, end])\n    return merged\n",
        (
            Case("overlap", {"intervals": [[1, 3], [2, 5], [8, 9]]}, [[1, 5], [8, 9]]),
            Case("touch", {"intervals": [[1, 2], [2, 3]]}, [[1, 3]], True),
            Case("contained", {"intervals": [[1, 9], [2, 3]]}, [[1, 9]], True),
            Case("empty", {"intervals": []}, [], True),
        ),
    ),
    Challenge(
        "find-duplicates",
        "Find Duplicates",
        "Data structures",
        "Return every integer that occurs more than once, exactly once, in ascending order.",
        "solve(nums: list[int]) -> list[int]. Negative values and zero are valid.",
        "0..10,000 integers.",
        "Reference: O(n + k log k) time, O(n) space; k duplicate values.",
        "def solve(nums):\n    seen, duplicates = set(), set()\n    for value in nums:\n        if value in seen:\n            duplicates.add(value)\n        seen.add(value)\n    return sorted(duplicates)\n",
        "def solve(nums):\n    seen, duplicates = set(), []\n    for value in nums:\n        if value in seen:\n            duplicates.append(value)\n        seen.add(value)\n    return sorted(duplicates)\n",
        (
            Case("normal", {"nums": [3, 1, 3, 2, 2]}, [2, 3]),
            Case("triple", {"nums": [4, 4, 4]}, [4], True),
            Case("negative", {"nums": [-1, 0, -1, 0]}, [-1, 0], True),
            Case("empty", {"nums": []}, [], True),
        ),
    ),
    Challenge(
        "reverse-linked-list",
        "Reverse Linked List",
        "Data structures",
        "Reverse an acyclic linked chain supplied as a JSON node table.",
        'solve(nodes: list[dict], head: int | None) -> dict. Nodes have "value" and "next" (index or null). Return {"nodes": node_table, "head": index_or_null}; reverse pointers in a new table, retaining node order and values.',
        "0..5,000 nodes; all nodes reachable exactly once from head; empty uses head=null.",
        "Reference: O(n) time and O(n) space for a copy; O(1) pointer state.",
        'def solve(nodes, head):\n    result = [dict(node) for node in nodes]\n    previous = None\n    current = head\n    while current is not None:\n        following = result[current]["next"]\n        result[current]["next"] = previous\n        previous, current = current, following\n    return {"nodes": result, "head": previous}\n',
        'def solve(nodes, head):\n    result = [dict(node) for node in nodes]\n    current = head\n    previous = None\n    while current is not None:\n        following = result[current]["next"]\n        result[current]["next"] = previous\n        previous, current = current, following\n    return {"nodes": result, "head": head}\n',
        (
            Case(
                "two",
                {"nodes": [{"value": 1, "next": 1}, {"value": 2, "next": None}], "head": 0},
                {"nodes": [{"value": 1, "next": None}, {"value": 2, "next": 0}], "head": 1},
            ),
            Case("empty", {"nodes": [], "head": None}, {"nodes": [], "head": None}, True),
            Case(
                "single",
                {"nodes": [{"value": 9, "next": None}], "head": 0},
                {"nodes": [{"value": 9, "next": None}], "head": 0},
                True,
            ),
        ),
    ),
    Challenge(
        "data-validation",
        "Data Validation",
        "Business automation",
        "Validate imported inventory records without silently discarding bad rows.",
        'solve(rows: list[dict]) -> dict. Return {"valid_ids": [...], "invalid_indices": [...]}, preserving order. A row requires a non-empty string id and non-boolean integer quantity >= 0. Missing or wrong-type fields invalidate it. Extra fields are allowed; ids need not be unique.',
        "0..5,000 JSON object rows.",
        "Reference: O(n) time and O(n) output space.",
        'def solve(rows):\n    valid, invalid = [], []\n    for i, row in enumerate(rows):\n        ident, qty = row.get("id"), row.get("quantity")\n        if isinstance(ident, str) and ident.strip() and type(qty) is int and qty >= 0:\n            valid.append(ident)\n        else:\n            invalid.append(i)\n    return {"valid_ids": valid, "invalid_indices": invalid}\n',
        'def solve(rows):\n    valid, invalid = [], []\n    for i, row in enumerate(rows):\n        if row.get("id") and isinstance(row.get("quantity"), int) and row["quantity"] >= 0:\n            valid.append(row["id"])\n        else:\n            invalid.append(i)\n    return {"valid_ids": valid, "invalid_indices": invalid}\n',
        (
            Case(
                "normal",
                {"rows": [{"id": "a", "quantity": 2}, {"id": "b", "quantity": -1}]},
                {"valid_ids": ["a"], "invalid_indices": [1]},
            ),
            Case(
                "boolean",
                {"rows": [{"id": "a", "quantity": True}]},
                {"valid_ids": [], "invalid_indices": [0]},
                True,
            ),
            Case(
                "whitespace",
                {"rows": [{"id": "  ", "quantity": 0}, {"quantity": 2}]},
                {"valid_ids": [], "invalid_indices": [0, 1]},
                True,
            ),
            Case("empty", {"rows": []}, {"valid_ids": [], "invalid_indices": []}, True),
        ),
    ),
    Challenge(
        "csv-processing",
        "CSV Processing",
        "Business automation",
        "Aggregate quantities by product from a small comma-delimited export.",
        "solve(text: str) -> dict[str, int]. Required header: product,quantity. Use CSV quoting rules. Strip product names; reject blank names and malformed rows with ValueError. Quantity must be an ASCII non-negative integer. Preserve product case. Header-only input returns {}.",
        "0..5,000 rows; valid UTF-8 text; no extra columns; rows have exactly two fields.",
        "Reference: O(n + text length) time and O(k) space, k products.",
        'import csv\nimport io\nimport re\n\ndef solve(text):\n    reader = csv.reader(io.StringIO(text), strict=True)\n    try:\n        header = next(reader, None)\n        if header != ["product", "quantity"]:\n            raise ValueError("Expected product,quantity header")\n        totals = {}\n        for row in reader:\n            if len(row) != 2 or not row[0].strip() or not re.fullmatch(r"[0-9]+", row[1]):\n                raise ValueError("Invalid row")\n            name = row[0].strip()\n            totals[name] = totals.get(name, 0) + int(row[1])\n        return totals\n    except csv.Error as exc:\n        raise ValueError("Invalid CSV") from exc\n',
        'def solve(text):\n    totals = {}\n    for line in text.splitlines()[1:]:\n        name, quantity = line.split(",")\n        totals[name.strip()] = int(quantity)\n    return totals\n',
        (
            Case(
                "normal", {"text": "product,quantity\nDesk,2\nMouse,3\n"}, {"Desk": 2, "Mouse": 3}
            ),
            Case("repeat", {"text": "product,quantity\nDesk,2\nDesk,3\n"}, {"Desk": 5}, True),
            Case("quoted", {"text": 'product,quantity\n"Cable, USB",2\n'}, {"Cable, USB": 2}, True),
            Case("empty", {"text": "product,quantity\n"}, {}, True),
            Case(
                "negative", {"text": "product,quantity\nDesk,-1\n"}, {"raises": "ValueError"}, True
            ),
            Case("header", {"text": "wrong,header\n"}, {"raises": "ValueError"}, True),
        ),
    ),
]
REGISTRY = {challenge.id: challenge for challenge in CHALLENGES}


def trusted_code(challenge: Challenge, variant: str | None) -> str:
    if variant == "reference":
        return challenge.reference
    if variant == "buggy":
        return challenge.buggy
    if challenge.id == "two-sum":
        fixtures = {
            "syntax-error": "def solve(:\n",
            "runtime-error": "def solve(**kwargs):\n    raise RuntimeError('Demonstration exception')\n",
            "timeout": "def solve(**kwargs):\n    while True:\n        pass\n",
        }
        if variant in fixtures:
            return fixtures[variant]
    raise ValueError("Unknown trusted example")
