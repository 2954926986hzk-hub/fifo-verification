
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer


DEPTH = 16
DATA_MASK = 0xFF


async def cycle(dut, rst=0, wr_en=0, rd_en=0, din=0):
    """在下降沿驱动输入，在上升沿后检查输出。"""
    await FallingEdge(dut.clk)

    dut.rst.value = rst
    dut.wr_en.value = wr_en
    dut.rd_en.value = rd_en
    dut.din.value = din

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


def check_flags(dut, model, step):
    """检查 FIFO 状态标志是否与参考模型一致。"""
    actual_empty = int(dut.empty.value)
    actual_full = int(dut.full.value)

    assert actual_empty == int(len(model) == 0), (
        f"step={step}: empty mismatch, occupancy={len(model)}, "
        f"actual={actual_empty}"
    )

    assert actual_full == int(len(model) == DEPTH), (
        f"step={step}: full mismatch, occupancy={len(model)}, "
        f"actual={actual_full}"
    )


@cocotb.test()
async def test_fifo_stress(dut):
    """检查复位、边界条件、指针回绕和随机读写。"""

    dut.clk.value = 0
    dut.rst.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. 复位
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    assert int(dut.empty.value) == 1, "Reset should set empty"
    assert int(dut.full.value) == 0, "Reset should clear full"
    assert int(dut.dout.value) == 0, "Reset should clear dout"

    model = []

    await cycle(dut, rst=0)
    check_flags(dut, model, "after reset")

    # 2. 空 FIFO 同时读写
    # 设计应拒绝读取，但允许写入一个新值。
    await cycle(dut, wr_en=1, rd_en=1, din=0xA1)
    model.append(0xA1)
    check_flags(dut, model, "empty simultaneous read/write")

    # 3. 读出刚才写入的数据
    await cycle(dut, rd_en=1)
    actual = int(dut.dout.value)
    expected = model.pop(0)

    assert actual == expected, (
        f"Empty-boundary recovery mismatch: "
        f"expected={expected:#04x}, actual={actual:#04x}"
    )
    check_flags(dut, model, "after draining empty-boundary write")

    # 4. 写满 FIFO
    for i in range(DEPTH):
        value = (i * 13 + 7) & DATA_MASK
        await cycle(dut, wr_en=1, din=value)
        model.append(value)
        check_flags(dut, model, f"fill {i}")

    assert int(dut.full.value) == 1, "FIFO should be full"

    # 5. 满状态下同时读写
    # RTL 的 !full 条件会拒绝写入，但 !empty 允许读取。
    expected = model.pop(0)
    await cycle(dut, wr_en=1, rd_en=1, din=0xEE)

    actual = int(dut.dout.value)
    assert actual == expected, (
        f"Full-boundary simultaneous operation mismatch: "
        f"expected={expected:#04x}, actual={actual:#04x}"
    )
    check_flags(dut, model, "full simultaneous read/write")

    # 6. 排空 FIFO，验证顺序
    while model:
        expected = model.pop(0)
        await cycle(dut, rd_en=1)
        actual = int(dut.dout.value)

        assert actual == expected, (
            f"Drain mismatch: expected={expected:#04x}, "
            f"actual={actual:#04x}"
        )

        check_flags(dut, model, "drain")

    # 7. 多轮写入和读取，检查指针回绕
    for round_id in range(5):
        values = [
            (round_id * 31 + i * 7) & DATA_MASK
            for i in range(DEPTH)
        ]

        for value in values:
            await cycle(dut, wr_en=1, din=value)
            model.append(value)
            check_flags(dut, model, f"wrap fill round {round_id}")

        for expected in values:
            model.pop(0)
            await cycle(dut, rd_en=1)
            actual = int(dut.dout.value)

            assert actual == expected, (
                f"Wraparound mismatch: expected={expected:#04x}, "
                f"actual={actual:#04x}"
            )

            check_flags(dut, model, f"wrap drain round {round_id}")

    # 8. 随机读写压力测试
    rng = random.Random(20261019)

    for step in range(2000):
        wr_en = rng.randint(0, 1)
        rd_en = rng.randint(0, 1)
        din = rng.randint(0, DATA_MASK)

        # 按当前占用状态，预测本周期哪些操作会被 RTL 接受。
        do_write = bool(wr_en and len(model) < DEPTH)
        do_read = bool(rd_en and len(model) > 0)

        # 先保存本周期读取的期望值。
        expected = model[0] if do_read else None

        await cycle(dut, wr_en=wr_en, rd_en=rd_en, din=din)

        if do_read:
            actual = int(dut.dout.value)
            assert actual == expected, (
                f"Random step {step}: data mismatch, "
                f"expected={expected:#04x}, actual={actual:#04x}, "
                f"occupancy_before={len(model)}"
            )
            model.pop(0)

        if do_write:
            model.append(din)

        check_flags(dut, model, f"random step {step}")

    # 9. 最后排空，验证所有剩余数据
    while model:
        expected = model.pop(0)

        await cycle(dut, rd_en=1)
        actual = int(dut.dout.value)

        assert actual == expected, (
            f"Final drain mismatch: expected={expected:#04x}, "
            f"actual={actual:#04x}"
        )

        check_flags(dut, model, "final drain")

    dut._log.info(
        "PASS: reset, empty/full boundaries, simultaneous operations, "
        "pointer wraparound, and 2000 randomized cycles"
    )

