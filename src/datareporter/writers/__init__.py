"""Document writers (PDF, Obsidian Markdown, ASCII data export).

Writers are pure assembly: they consume pre-rendered PNG images and
metadata collected by the render workers and never open HDF5 files
(the ASCII exporter is the one exception — it exports raw curve data
and does its HDF5 reads inside its own worker pool).
"""
