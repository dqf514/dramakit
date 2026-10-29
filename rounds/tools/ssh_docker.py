"""What was the ComfyUI container on the other machine configured like?"""
import json
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c):
    c = f"echo '{pw}' | sudo -S bash -c \"{c}\""
    _in, out, err = cli.exec_command(c, timeout=120)
    return out.read().decode("utf-8", "replace").strip()


o = run("docker inspect comfyui 2>&1")
try:
    d = json.loads(o)[0]
    cfg = d.get("Config", {})
    host_cfg = d.get("HostConfig", {})
    print("镜像:", cfg.get("Image"))
    print("命令:", cfg.get("Cmd"))
    print("入口:", cfg.get("Entrypoint"))
    print("工作目录:", cfg.get("WorkingDir"))
    print("环境:", json.dumps(cfg.get("Env", []), ensure_ascii=False)[:900])
    print("挂载:", json.dumps(host_cfg.get("Binds", []), ensure_ascii=False))
    print("端口:", json.dumps(host_cfg.get("PortBindings", {}), ensure_ascii=False))
    print("设备:", json.dumps(host_cfg.get("DeviceRequests", []), ensure_ascii=False)[:400])
    print("重启策略:", host_cfg.get("RestartPolicy"))
    print("状态:", d.get("State", {}).get("Status"),
          d.get("State", {}).get("ExitCode"),
          d.get("State", {}).get("Error"))
except Exception as e:  # noqa: BLE001
    print("解析失败:", e)
    print(o[:1500])

print("\n=== vllm 容器的启动参数 ===")
o = run("docker inspect vllm-qwen38 --format '{{json .Config.Cmd}} {{json .HostConfig.Binds}}' 2>&1")
print(o[:1200])
cli.close()
