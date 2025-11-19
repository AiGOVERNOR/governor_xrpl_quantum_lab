"""
ecosystem

XRPL VQM Ecosystem package.

This package wires together:
- A read-only XRPL RPC client (xrpl_rpc.XRPL_RPC)
- The XRPLGuardian safety/coordination layer
- Orchestrators and CLI entrypoints

All logic here is advisory / proposal-only. It does NOT submit
transactions or manage secrets.
"""
