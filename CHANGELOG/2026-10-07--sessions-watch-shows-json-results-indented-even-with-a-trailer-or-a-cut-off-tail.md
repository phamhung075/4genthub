## Sessions watch shows JSON results indented even with a trailer or a cut-off tail

- `scripts/openrig_watch_tools.py` `pretty()` only indented a result that was wholly valid JSON, so results ending in
  `Wall time: ...` or cut by the log at 768 characters stayed on one line. It now indents the leading JSON value and
  keeps what follows as it is; JSON cut mid-value is indented by the new `indent_cut_json`. Tested by three specs.
