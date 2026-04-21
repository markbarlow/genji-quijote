"""Text loading module with BOM and line ending normalisation."""

from pathlib import Path
from typing import Union


def load_text(path: Union[str, Path]) -> str:
    """
    Load a text file and normalise encoding and line endings.

    Opens a source text file, strips the UTF-8 BOM if present, and normalises
    CRLF line endings to LF. Returns a clean unicode string ready for
    downstream processing.

    Parameters
    ----------
    path : str | Path
        Path to the text file to load.

    Returns
    -------
    str
        The file contents with UTF-8 BOM removed and CRLF converted to LF.

    """
    # Convert to Path object if string is provided
    path = Path(path)

    # Read file as UTF-8
    content = path.read_text(encoding="utf-8")

    # Strip UTF-8 BOM if present (appears as \ufeff at start of string)
    if content.startswith("\ufeff"):
        content = content[1:]

    # Normalise CRLF line endings to LF
    content = content.replace("\r\n", "\n")

    return content
