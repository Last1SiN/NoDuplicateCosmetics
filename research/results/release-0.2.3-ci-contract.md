# 0.2.3 CI contract

The release CI verifies:

- Python source parses/compiles without generating committed bytecode;
- `project.version` and `tool.sdkmod.version` agree;
- `coop_support` remains `Unknown`;
- supported game remains BL3;
- no committed `__pycache__`, `.pyc` or `.pyo` files;
- generated `.sdkmod` has exactly one root folder whose name matches the archive stem;
- the 0.2.3 release branch and PR keep the exact tested production source SHA256 `576ed747bd11cbdf9171dfb666b08dc45519185d76afbff0f5090c7a959cd137`.
