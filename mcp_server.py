import asyncio, random, json
from bleak import BleakClient
from fastmcp import FastMCP

ADDR = "你的设备蓝牙地址"  # 替换为你的设备地址，例如 "03:0F:55:78:47:AE"
CHAR = "0000ee03-0000-1000-8000-00805f9b34fb"

CHANNELS = {
    "振动": (0x01, 0x02),
    "吮吸": (0x07, 0x08),
    "微电流": (0x03, 0x04),
}

def build_packet(ch_id, ch_en, intensity):
    return bytes([random.randint(0,255), 0x01, 0x00, 0x02, 0x00,
                  ch_id, 0x11, intensity, 0x00, ch_en, 0x11, 0x01])

class SosexyController:
    def __init__(self):
        self.client = None
        self._lock = asyncio.Lock()

    async def ensure_connected(self):
        if self.client is not None and self.client.is_connected:
            return
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        self.client = BleakClient(ADDR)
        await asyncio.wait_for(self.client.connect(), timeout=10)
        print(f"BLE 已连接 {ADDR}")

    async def write_channel(self, channel: str, intensity: int):
        async with self._lock:
            await self.ensure_connected()
            try:
                ch_id, ch_en = CHANNELS[channel]
                await self.client.write_gatt_char(
                    CHAR, build_packet(ch_id, ch_en, intensity), response=True)
            except Exception:
                print("断线重连...")
                await self.ensure_connected()
                ch_id, ch_en = CHANNELS[channel]
                await self.client.write_gatt_char(
                    CHAR, build_packet(ch_id, ch_en, intensity), response=True)

    async def run_steps(self, steps: list) -> list:
        results = []
        for s in steps:
            channel, intensity, duration = s["channel"], s["intensity"], s["duration"]
            ch_id, ch_en = CHANNELS[channel]
            await self.write_channel(channel, intensity)
            elapsed = 0.0
            while elapsed < duration:
                wait = min(1.0, duration - elapsed)
                await asyncio.sleep(wait)
                elapsed += wait
                if elapsed < duration:
                    async with self._lock:
                        await self.client.write_gatt_char(
                            CHAR, build_packet(ch_id, ch_en, intensity), response=True)
            await self.write_channel(channel, 0)
            results.append(f"{channel}{intensity}强度{duration}秒")
        return results

controller = SosexyController()
mcp = FastMCP("SOSEXY")

@mcp.tool()
async def set_vibrate(intensity: int) -> str:
    """设置震动强度并持续保持，intensity 0-100，0为停止，立即返回"""
    await controller.write_channel("振动", intensity)
    return f"震动设为{intensity}"

@mcp.tool()
async def set_suck(intensity: int) -> str:
    """设置吮吸强度并持续保持，intensity 0-100，0为停止，立即返回"""
    await controller.write_channel("吮吸", intensity)
    return f"吮吸设为{intensity}"

@mcp.tool()
async def set_microcurrent(intensity: int) -> str:
    """设置微电流强度并持续保持，intensity 0-100，0为停止，立即返回"""
    await controller.write_channel("微电流", intensity)
    return f"微电流设为{intensity}"

@mcp.tool()
async def stop_all() -> str:
    """停止所有马达"""
    for ch in ["振动", "吮吸", "微电流"]:
        await controller.write_channel(ch, 0)
    return "全部停止"

@mcp.tool()
async def run_sequence(steps_json: str) -> str:
    """按顺序执行多步指令，steps_json是JSON数组，每项包含channel/intensity/duration"""
    steps = json.loads(steps_json)
    results = await controller.run_steps(steps)
    return "序列完成：" + " → ".join(results)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8888)
