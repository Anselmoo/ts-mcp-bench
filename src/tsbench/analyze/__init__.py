"""Offline analyses of a scored run folder: the code of the runs (`snippets`), their solution strategies
(`strategy`), the failing tool steps (`errors`), the origin of each answer number (`provenance`) and the effort and
time per run (`effort`). Each is one `tsbench analyze <part>` command that reads transcripts, sidecars and score
tables and writes CSV tables and a README into a folder outside the run folder; nothing is executed and no model is
called."""
