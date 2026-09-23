# API docstring examples

Use realistic interview variables and full object paths, such as `users[0].incomes[0].total()`
and `users[0].address.on_one_line()`. Prefer Mako question text and Jinja2 DOCX
examples; use YAML `code:` blocks for interview logic. Do not use Python REPL prompts.

When sample output helps explain a public API, state the example's data and relevant
language or formatting settings. Label fenced input blocks with **Input (Mako)**,
**Input (Jinja2)**, or **Input (interview YAML)**. Follow them with **Output** and a
separate `text` fenced block containing the exact result. If both template examples
produce the same result, share one output block. For a code block that assigns a
variable, identify which variable's value is shown. Internal helpers do not normally
need output examples.

Keep blank lines around labels and fences. Align fences with the docstring's base
indentation, even inside an `Example:` section: the Google-style processor in
`AssemblyLine-docs` preserves extra code indentation, which Markdown would render
as literal fence markers. Keep YAML/Python indentation inside each fence. Use
ordinary bold labels and fenced code, so no custom Docusaurus components are needed.
