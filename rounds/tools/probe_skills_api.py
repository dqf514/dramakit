import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/api/skills", timeout=30) as r:
    raw = r.read().decode("utf-8")
print("  开头:", raw[:220])
