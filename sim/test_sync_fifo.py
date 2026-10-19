
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


DEPTH = 16
DATA_WIDTH = 8
MASK = (1 << DATA_WIDTH) - 1


async def cycle(dut, rst, wr_en, rd_en, din):
    """在下降沿设置输入，在上升沿采样更新后的输出。"""
    await FallingEdge(dut.clk)

    dut.rst.value = rst
    dut.wr_en.value = wr_en
    dut.rd_en.value = rd_en
    dut.din.value = din

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_fifo_reference_queue(dut):
    """用 Python 参考队列检查 FIFO 的数据和状态。"""

    dut.clk.value = 0
    dut.rst.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 先完成复位
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    assert int(dut.empty.value) == 1
    assert int(dut.full.value) == 0

    await cycle(dut, 0, 0, 0, 0)

    # Python 参考队列：保存理论上应在 FIFO 中的数据
    model = []

    # 固定随机种子，确保每次测试可以复现
    rng = random.Random(20261018)

    # 先写入并读出一整轮，检查指针回绕
    for i in range(DEPTH):
        value = (i * 17 + 3) & MASK

        await cycle(dut, 0, 1, 0, value)

        assert len(model) < DEPTH
        model.append(value)

        assert int(dut.full.value) == (len(model) == DEPTH)
        assert int(dut.empty.value) == 0

    # 满状态下额外写入应该被忽略
    await cycle(dut, 0, 1, 0, 0xEE)
    assert len(model) == DEPTH
    assert int(dut.full.value) == 1

    for expected in list(model):
        await cycle(dut, 0, 0, 1, 0)

        actual = int(dut.dout.value)
        assert actual == expected, (
            f"FIFO order mismatch: expected={expected:#04x}, "
            f"actual={actual:#04x}"
        )

        model.pop(0)

    assert int(dut.empty.value) == 1

    # 随机读写：模型只在实际允许的操作发生时更新
    for step in range(500):
        wr_en = rng.randint(0, 1)
        rd_en = rng.randint(0, 1)
        din = rng.randint(0, MASK)

        # 该 FIFO 在满时拒绝写入，在空时拒绝读取。
        # 同时读写时，允许的操作根据当前状态独立判断。
        do_write = bool(wr_en and len(model) < DEPTH)
        do_read = bool(rd_en and len(model) > 0)

        expected_read = model[0] if do_read else None

        await cycle(dut, 0, wr_en, rd_en, din)

        if do_read:
            actual = int(dut.dout.value)
            assert actual == expected_read, (
                f"step={step}: expected={expected_read:#04x}, "
                f"actual={actual:#04x}, occupancy={len(model)}"
            )
            model.pop(0)

        if do_write:
            model.append(din)

        assert int(dut.empty.value) == (len(model) == 0), (
            f"step={step}: empty flag mismatch, occupancy={len(model)}"
        )
        assert int(dut.full.value) == (len(model) == DEPTH), (
            f"step={step}: full flag mismatch, occupancy={len(model)}"
        )

    # 最后排空，确认剩余数据仍然按先进先出顺序输出
    while model:
        expected = model[0]

        await cycle(dut, 0, 0, 1, 0)

        actual = int(dut.dout.value)
        assert actual == expected, (
            f"Drain mismatch: expected={expected:#04x}, actual={actual:#04x}"
        )

        model.pop(0)

    assert int(dut.empty.value) == 1
    assert int(dut.full.value) == 0

    dut._log.info(
        "PASS: reference queue, wraparound, full/empty, "
        "and 500 randomized cycles"
    )
