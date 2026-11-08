"""Put the card machine's memory right, the moment it can be reached.

The machine runs two ComfyUI workers, and between them they hold
ninety-six gigabytes of weights on a machine with a hundred and twenty-
one. ComfyUI's own accounting does not know the other worker is there:
on Linux it allows itself up to a hundred and nine gigabytes of pinned
memory per process, and pinned pages cannot be swapped out. So when the
machine runs short the kernel kills a worker, and the machine stops
answering - which is what "the card died" looks like from here.

The fix is three things, all of them things the container can be told:

  --fast-disk             the weights are read from the disk as they are
                          needed instead of being held in memory
  --disable-pinned-memory the fast offload path, which is what pins, is
                          off; ordinary pages can be swapped
  shm_size 2gb            each container was allowed eight gigabytes of
                          shared memory; two of them is sixteen

And more swap, so that a peak is something the kernel rides out rather
than something it kills.

This waits for the machine to answer, does all of it, and says what
happened.
"""
import json
import subprocess
import time
from pathlib import Path

SSH = ["ssh", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
       "-o", "BatchMode=yes", "david@192.168.31.8"]
SCP = ["scp", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
       "-o", "BatchMode=yes"]
COMPOSE = Path(r"E:\dramakit\rounds\tools\docker-compose.h3.yml")
LOG = Path(r"C:\Users\David\AppData\Local\Temp\opencode\remote_fix.txt")
REMOTE_COMPOSE = "/home/david/dramakit/docker-compose.h3.yml"


def note(lines):
    with LOG.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for l in lines:
        print(l, flush=True)


def sh(cmd, timeout=180):
    try:
        r = subprocess.run(SSH + [cmd], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (r.returncode, (r.stdout or "") + (r.stderr or ""))
    except subprocess.TimeoutExpired:
        return 124, "超时"
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


def main():
    note([f"=== 等远端能进（{time.strftime('%H:%M:%S')}）==="])
    deadline = time.time() + 6 * 3600
    tries = 0
    while time.time() < deadline:
        tries += 1
        code, out = sh("echo OK", timeout=60)
        if code != 0:
            if tries % 5 == 1:
                note([f"[{time.strftime('%H:%M:%S')}] 第 {tries} 次：还进不去"])
            time.sleep(40)
            continue

        note([f"[{time.strftime('%H:%M:%S')}] 进得去了（第 {tries} 次）"])
        note(["  内存:", "  " + sh("free -g | head -3")[1].strip()])
        note(["  /data 是什么盘:", "  " + sh(
            "lsblk -o NAME,SIZE,TYPE,ROTA,MOUNTPOINT 2>/dev/null | grep -E 'nvme|NAME' | head -6"
        )[1].strip()])

        # 1) more swap: a peak is something to ride out, not to die of
        note(["--- 加 swap ---"])
        note(["  " + sh(
            "swapon --show | tail -n +2 | awk '{print $1}' | grep -qx /data/swap2.img || "
            "(fallocate -l 24G /data/swap2.img && chmod 600 /data/swap2.img && "
            "mkswap /data/swap2.img >/dev/null && swapon /data/swap2.img && echo added || echo failed)"
        )[1].strip()])
        note(["  " + sh("free -g | tail -2")[1].strip()])

        # 2) the new container settings
        note(["--- 换容器配置 ---"])
        subprocess.run(SCP + [str(COMPOSE), "david@192.168.31.8:" + REMOTE_COMPOSE],
                       capture_output=True, timeout=180)
        note(["  " + sh(
            "cd ~/dramakit && docker compose -f docker-compose.h3.yml config >/dev/null 2>&1 "
            "&& echo '配置是对的' || echo '配置有问题'"
        )[1].strip()])

        note(["--- 重启两个容器 ---"])
        code, out = sh(
            "cd ~/dramakit && docker compose -f docker-compose.h3.yml up -d --force-recreate "
            "2>&1 | tail -6", timeout=600)
        note(["  " + out.strip()[-800:]])

        note(["--- 等它们起来 ---"])
        for _ in range(20):
            time.sleep(20)
            ok = 0
            for p in (8188, 8189):
                c, o = sh("curl -s -o /dev/null -w '%{http_code}' --max-time 15 "
                          f"http://127.0.0.1:{p}/queue")
                ok += 1 if o.strip() == "200" else 0
                note([f"    :{p} -> {o.strip()}"])
            if ok == 2:
                break
        note(["--- 起来之后的内存 ---"])
        note(["  " + sh("free -g | head -3")[1].strip()])
        note(["  " + sh("ps -eo rss=,comm= --sort=-rss | head -5 | "
                       "awk '{printf \"%.1f GB  %s\\n\", $1/1048576, $2}'")[1].strip()])
        note([f"[{time.strftime('%H:%M:%S')}] 完了"])
        return 0
    note([f"=== 等了 {tries} 次还没进去，放弃 ==="])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
