# Copyright 2026 Dimensional Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def skill(func: F | None = None, *, return_direct: bool = False) -> F | Callable[[F], F]:
    def decorator(fn: F) -> F:
        fn.__rpc__ = True  # type: ignore[attr-defined]
        fn.__skill__ = True  # type: ignore[attr-defined]
        fn.__return_direct__ = return_direct  # type: ignore[attr-defined]
        return fn

    if func is not None:
        # Called as @skill (no arguments)
        return decorator(func)
    # Called as @skill(return_direct=True)
    return decorator  # type: ignore[return-value]
