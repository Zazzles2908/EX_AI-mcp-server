# Core

Runtime server, routing, configuration, logging, and common utilities will live here after Phase 2 moves.

- server/ (entry points, handlers)
- config.py, constants.py
- utils/ (pathing, serialization, client detection generalized)

A thin shim at repo root (server.py) will import from src/core after moves.
