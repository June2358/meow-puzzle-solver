"""``python -m meow``로 pygame 앱을 실행한다."""

import asyncio

from .app import main

if __name__ == "__main__":
    asyncio.run(main())
