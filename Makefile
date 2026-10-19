TOPLEVEL_LANG = verilog
SIM = icarus

VERILOG_SOURCES = $(PWD)/rtl/sync_fifo.v
TOPLEVEL = sync_fifo
COCOTB_TEST_MODULES = test_sync_fifo

export PYTHONPATH := $(PWD)/sim:$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim

