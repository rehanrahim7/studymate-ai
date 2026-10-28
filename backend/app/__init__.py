"""StudyMate AI backend package.

PyTorch and FAISS each bundle an OpenMP runtime on macOS. Loading both in the
same process can crash at an OpenMP barrier, so configure a single worker
thread and let the Intel runtime tolerate the duplicate library before either
dependency is imported anywhere in the process.
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
