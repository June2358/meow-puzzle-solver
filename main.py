"""Pygbag과 호환되는 앱 진입점."""

import asyncio

import pygame  # noqa: F401  # Pygbag이 pygame WebAssembly 모듈을 미리 불러오게 한다.

from meow.app import main

if __name__ == "__main__":
    asyncio.run(main())
