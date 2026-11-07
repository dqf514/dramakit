import json
import urllib.request


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request("http://127.0.0.1:8080" + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


print(" ", json.dumps(post("/api/jobs/stop", {}), ensure_ascii=False))
