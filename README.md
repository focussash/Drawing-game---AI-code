# 你画我猜

给朋友们一起玩的网页版你画我猜。用手机浏览器打开链接就能玩，不用装 App，电脑浏览器也可以。

- 规则、时长、人数、颜色等都在 `config.toml` 里改
- 词库是 `words/` 文件夹里的 txt 文件，想加就加
- 玩法做成了可替换的"模式"，以后可以加联想模式之类的新玩法

---

## 一、在家里玩（同一个 Wi-Fi）

1. 双击 **`start-server.bat`**。命令行里也可以运行：
   ```
   "E:\MiniConda\envs\biomotum\python.exe" main.py
   ```
2. 窗口里会显示两个地址：
   ```
   本机打开:      http://localhost:8000
   同一 Wi-Fi 下: http://10.0.0.231:8000
   ```
3. 连着同一个 Wi-Fi 的手机打开第二个地址，点「创建房间」，再把房间链接发给其他人。

**手机打不开？** 第一次启动时，Windows 防火墙可能会弹窗询问，选"允许 Python 访问专用网络"。如果当时点了拒绝，到"Windows 安全中心 → 防火墙 → 允许应用通过防火墙"里把 Python 勾上。

## 二、让外地的朋友也能进来

一共三种办法，从上往下越来越稳定，但也越来越麻烦。

### 方案 A：临时公网地址（最快，几分钟搞定）

双击 **`start-online.bat`**（命令行等价于 `python main.py --online`）。它会在**同一个窗口**里：

1. 启动游戏服务器。这时服务器**只接受公网地址转来的连接**，同一个网络（比如校园网）里的其他人不能直接连你的 IP；
2. 用 Windows 自带的 `ssh` 连到免费服务 [localhost.run](https://localhost.run)，拿到一个 `https://xxxx.lhr.life` 的网址。

把这个网址发给朋友就行。**关掉这个窗口，服务器和公网地址会一起关闭**；如果公网连接自己断了，服务器也会跟着停。端口用的是 `config.toml` 里的 `port`。

- **优点**：不用注册，不用装软件，也不用碰路由器。
- **缺点**：
  - 网址每次都不一样，关掉窗口就失效；
  - 免费服务的速度和稳定性没有保证，国内能不能顺畅打开也不一定；
  - **拿到网址的任何人都能进来**，别把网址发到公开的地方。
- 第一次运行时，ssh 可能会问 `Are you sure you want to continue connecting`，输入 `yes` 回车。

> 2026-10-22 实测可用：用手机流量能打开并正常玩。国内能不能顺畅打开还没测过；如果打不开，或者游戏里一直显示"正在重新连接"，就换方案 B 或 C。

### 方案 B：路由器端口转发（家里电脑当服务器）

1. 登录路由器管理页面（一般是 `192.168.1.1` 或 `10.0.0.1`），找到"端口转发 / 虚拟服务器"，把**外部端口 8000** 转发到**这台电脑的 IP（例如 10.0.0.231）的 8000 端口**。
2. 在 Windows 防火墙里放行 8000 端口（TCP，入站）。
3. 用 [ip.sb](https://ip.sb) 之类的网站查到你的公网 IP，朋友打开 `http://公网IP:8000`。

**注意：**
- 很多宽带没有真正的公网 IP（运营商级 NAT）。如果路由器上显示的 WAN 地址和 ip.sb 查到的不一样，这个方案就用不了。
- 家里 IP 可能会变，可以配合 DDNS 使用。
- 电脑要一直开着。

### 方案 C：租一台 VPS（长期玩最推荐）

一台每月几美元的 Linux 小服务器就够用。选机房时考虑三地的朋友：

- **美国洛杉矶**：要选带国内优化线路的，比如标着 CN2 GIA 的。
- **日本东京**：离国内近，离美国也不算远。

这两个地方到美东、美中、国内的延迟都比较平均。服务器在境外，不需要备案。

在 Ubuntu 上部署：

```bash
# 1. 装 Python，把项目放到 /opt/nhwc（用 git clone 或者 scp 上传都行）
sudo apt update && sudo apt install -y python3 python3-venv
sudo useradd --system --home /opt/nhwc nhwc
sudo mkdir -p /opt/nhwc && sudo chown nhwc /opt/nhwc
# ……把项目文件放进 /opt/nhwc ……

# 2. 建虚拟环境，装依赖
cd /opt/nhwc
sudo -u nhwc python3 -m venv .venv
sudo -u nhwc .venv/bin/pip install -r requirements.txt

# 3. 设成开机自启、崩了自动重启
sudo cp deploy/nhwc.service /etc/systemd/system/
sudo systemctl enable --now nhwc
sudo systemctl status nhwc        # 看到 active (running) 就好了

# 4. 在 VPS 的防火墙或安全组里放行 8000 端口
```

然后朋友打开 `http://VPS的IP:8000`。

想要正式的域名和 https（微信里更不容易被拦截）：买个域名指向 VPS，再装 [Caddy](https://caddyserver.com)。在它的配置里写 `你的域名 { reverse_proxy 127.0.0.1:8000 }`，它会自动申请证书。页面会自动改用 `wss://`，不用改代码。

## 三、改配置

所有可调的东西都在 **`config.toml`** 里，每一项都有注释。改完后**重启服务器**才会生效。常用的几项：

| 想改什么 | 配置项 |
|---|---|
| 一个房间最多几个人 | `[room] max_players` |
| 至少几个人才能开始 | `[room] min_players` |
| 画画的颜色、粗细档位 | `[drawing] colors / brush_sizes / eraser_sizes` |
| 每局的默认设置：圈数、作画时长、缩短倒计时、加时等 | `[modes.classic]` |
| 计分 | `[modes.classic.scoring]` |
| 端口 | `[server] port` |

每局的设置（词库、圈数、时长、是否显示字数等），房主也可以在等待界面里直接改，只对这个房间生效。

配置写错时，服务器启动会直接报错，并告诉你是哪一项错了。

## 四、加词库

- 在 `words/` 文件夹里新建一个 `.txt`，文件名就是词库名，比如 `动物.txt`。
- 一行一个词。空行会被忽略，`#` 开头的行是注释，重复的词会自动去掉。
- 编码用 UTF-8 或 GBK 都行。用 Windows 记事本直接保存的文件也能读。
- **不用重启**：回到等待界面，就能在设置里勾选新词库。

## 五、常见问题

- **在微信里打开很卡、老断线？** 点右上角「···」，选「在浏览器打开」。页面上方也会有这个提示。
- **切到别的 App 再回来？** 会自动重连，分数和进度都还在。
- **画手掉线了？** 等 15 秒，这一轮会自动跳过。
- **房主掉线了？** 60 秒后房主会自动交给下一个人。
- **一个人在两个页面同时打开？** 后打开的那个生效，前一个页面会提示"已在其他页面打开"。
- **服务器重启后？** 房间都会消失，需要重新建房间，因为数据只存在内存里。

---

## 开发

- 设计文档：`claude-memory/DESIGN.md`；开发计划：`claude-memory/DEVELOPMENT_PLAN.md`；进度：`claude-memory/achievements.md`
- 跑测试：
  ```
  "E:\MiniConda\envs\biomotum\python.exe" -m pytest -q
  node --test "tests/web/*.test.js"
  ```
- 结构：
  - `server/`：后端。游戏规则是纯逻辑，不碰网络，也不读真实时钟。
  - `server/modes/<模式名>/`：每种玩法一个文件夹。
  - `server/net/`：WebSocket 和网页服务。
  - `web/`：前端，原生 JS，不需要构建。
- **加一个新玩法**：后端在 `server/modes/` 下新建一个模式，实现 `server/modes/base.py` 里 `Mode` 的接口，再注册到 `server/modes/__init__.py`；前端在 `web/js/modes/` 下加 reducer 和 view，再注册到 `web/js/modes/index.js`；最后在 `config.toml` 里加一节 `[modes.新模式名]`。核心代码不用动。
