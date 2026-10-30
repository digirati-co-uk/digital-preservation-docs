# Preservation UI

> [!NOTE]
> This page is a stub. The Preservation UI is a Razor Pages web application over the Preservation API, used by archivists and digitisation staff to create and work on Deposits, upload files, edit METS and preserve Archival Groups. Only the parts that have needed explaining so far are written up.

## Access, rights and derived conditions

Every folder, file and logical range in a Deposit has a **Metadata** control (the padlock, rights and database icons next to its name show what is currently set, in bold where it is set on that node and muted where it is inherited). Opening it shows a dialog with:

- **The restriction choice.** Labelled from the installation's [access condition profile](./02-Preservation-API.md#access-condition-profile) — for Leeds, *Protected Access Level*. A single choice, unless the profile allows several; choosing *(inherit from parent)* clears the node's own value so it takes its ancestor's.
- **The rights statement choice.** Also labelled from the profile — for Leeds, *Copyright Statement*. When the profile groups the statements, the dropdown shows only the grouped ones under their group headings; the three states described on the [writer page](./02b-METS-Written-by-the-Platform.md#rights-statement) are *(inherit from parent)*, *(none — do not inherit)* and a specific statement.
- **Any derived condition** — for Leeds, the *Access Tier*. This is never chosen. The dialog recomputes it as you change the two choices above, so you can see the consequence of a decision before saving. Where the result would depend on an inherited value the dialog cannot know (you have just cleared the node's own restriction, say), it says *inherits; determined on save* rather than guess; the value the server writes always comes from the node's effective inputs, and every save recomputes the whole document.
- **Record identifiers** and, for files, **file links**.

After saving, the tree shows the derived value alongside access and rights, in bold on the nodes that carry an explicit choice and muted on everything that inherits it.
