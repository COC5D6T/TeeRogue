# Contributing code to DDNet

## General

Please open an issue first discussing the idea before starting to write code.
It would be unfortunate if you spend time working on a contribution that does not align with the ideals of the DDNet project.

A non-exhaustive list of things that usually get rejected:
- Extending dummy with new gameplay-affecting features.
  https://github.com/ddnet/ddnet/pull/8275
  https://github.com/ddnet/ddnet/pull/5443#issuecomment-1158437505
- Breaking backwards compatibility in the network protocol or file formats such as skins and demos.
- Breaking backwards compatibility in gameplay:
	- Existing ranks should not be made impossible.
	- Existing maps should not break.
	- New gameplay should not make runs easier on already completed maps.

Check the [list of issues](https://github.com/ddnet/ddnet/issues) to find issues to work on.
Unlabeled issues have not been triaged yet and are usually not good candidates.
Furthermore, the label https://github.com/ddnet/ddnet/labels/needs-discussion indicates issues that still need discussion before they can be implemented and issues with the label https://github.com/ddnet/ddnet/labels/fix-changes-physics are too involved for new contributors.
