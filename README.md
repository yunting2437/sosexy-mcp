# sosexy-mcp

通过 MCP 协议让 Claude 直接控制啵啵贝玩具，支持序列控制和 SSH 远程接入（Windows）。

增加了序列控制，AI可自行排列关闭不同马达的强度时间档位，步骤之间无停顿，频率没有跑完Ai无法接受新消息。

人话版：由于个人xp，拙劣的仿制了APP端的失控模式，AI可以自己写一段频率，完全随机，没跑完就停不下来，频率变换不会有停顿感（可以玩强制:P），会类似于被操控的感觉（？）


> 蓝牙协议逆向基于 [51enuxu/sosexy-ble-control](https://github.com/51enuxu/sosexy-ble-control)，在此基础上增加了 MCP 接入、Windows SSH 隧道和序列控制。

---

## 和原仓库的区别

| | [51enuxu/sosexy-ble-control](https://github.com/51enuxu/sosexy-ble-control) | 本仓库 |
|--|--|--|
| 接入方式 | HTTP API，手动注册 tool | MCP 协议，Claude Code 自动接入 |
| 平台 | macOS | Windows |
| 序列控制 | 无 | 有（`run_sequence`） |
| 失控模式 | 无 | 有（见下方说明） |
| 多马达同控 | 有 | 有 |
| 持久 BLE 连接 | 有 | 有 |

---

## 架构

```
Claude（云端）── MCP ──► VPS ── SSH 反向隧道 ──► Windows ── BLE ──► 玩具
```

---

## 依赖

```bash
pip install bleak fastmcp
```

---

## 使用方法

### 第一步：找到设备蓝牙地址

打开设备管理器或用以下脚本扫描：

```python
import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover(timeout=10)
    for d in devices:
        print(d.name, d.address)

asyncio.run(scan())
```

找到名为 `SOSEXY` 的设备，记下地址（格式如 `03:0F:55:78:47:AE`），填入 `mcp_server.py` 的 `ADDR` 变量。

### 第二步：启动 MCP 服务

```powershell
python mcp_server.py
```

### 第三步：建立 SSH 反向隧道

> **注意**：Windows 上必须用 `127.0.0.1`，不能用 `localhost`，否则会因 IPv6/IPv4 解析问题导致隧道转发失败。

```powershell
ssh -i "C:\path\to\your\key" -N -R 8888:127.0.0.1:8888 user@your-vps.com
```

保持窗口开着，隧道会将 VPS 的 8888 端口映射到本机的 8888 端口。

### 第四步：配置 Claude Code（VPS 侧）

在项目目录下创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "sosexy": {
      "type": "http",
      "url": "http://localhost:8888/mcp"
    }
  }
}
```

在 `.claude/settings.json` 里允许工具调用：

```json
{
  "permissions": {
    "allow": ["mcp__sosexy__*"]
  }
}
```

---

## 工具说明

| 工具 | 说明 |
|--|--|
| `set_vibrate(intensity)` | 设置震动强度（0-100），立即返回，持续保持 |
| `set_suck(intensity)` | 设置吮吸强度（0-100），立即返回，持续保持 |
| `set_microcurrent(intensity)` | 设置微电流强度（0-100），立即返回，持续保持 |
| `stop_all()` | 停止所有马达 |
| `run_sequence(steps_json)` | 按顺序执行多步指令（见下方） |

### 序列控制

`run_sequence` 接收 JSON 数组，每步包含 `channel`（振动/吮吸/微电流）、`intensity`（0-100）、`duration`（秒）：

```json
[
  {"channel": "振动", "intensity": 50, "duration": 3},
  {"channel": "吮吸", "intensity": 30, "duration": 3},
  {"channel": "振动", "intensity": 80, "duration": 2}
]
```

步骤之间无停顿，BLE 连接在序列期间通过 keepalive 保持。

**序列执行期间 Claude 无法接收新消息**——这意味着一旦开始，在跑完之前停不下来。AI 可以自行排列震动、吮吸、微电流的强度、档位和时间，完全由 AI 决定节奏，类似于 APP 的失控模式，且频率没有跑完就无法对话。

示例（从低到高渐进，震动吮吸交替，中间穿插强度落差）：

```json
[
  {"channel": "振动", "intensity": 30, "duration": 4},
  {"channel": "吮吸", "intensity": 50, "duration": 3},
  {"channel": "振动", "intensity": 60, "duration": 3},
  {"channel": "吮吸", "intensity": 70, "duration": 2},
  {"channel": "振动", "intensity": 80, "duration": 2},
  {"channel": "吮吸", "intensity": 40, "duration": 4},
  {"channel": "振动", "intensity": 90, "duration": 3},
  {"channel": "吮吸", "intensity": 80, "duration": 3}
]
```

### 多马达同时控制

`set_*` 系列工具立即返回，可以连续调用开启多个马达同时运行：

```
set_vibrate(50) → set_suck(30) → 两个马达同时持续运行
stop_all()      → 全部停止
```

---

## 注意事项

- 序列执行期间 Claude 无法回复消息，总时长建议不超过 90 秒
- 玩具只能同时被一个程序连接，测试脚本和 MCP 服务不能同时跑
- SSH 隧道断开后需重新连接，MCP 服务不受影响

---

## 协议细节

见原仓库 [protocol.md](https://github.com/51enuxu/sosexy-ble-control/blob/main/protocol.md)。

---

## License

MIT

---

> 代码与文档由 [Claude](https://claude.ai) 完成，人类起到了草履虫的作用，有错误概不负责
