## before quit
77291     1 /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk
77323 77291 /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk
89746 77323 /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m mlx_lm server --model /Users/aa/LocalModelDesk/llms/Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit --host 127.0.0.1 --port 8767 --prompt-cache-bytes 51451002880 --prompt-cache-size 1
COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 77323   aa    4u  IPv4 0x7819a9c041f99b87      0t0  TCP 127.0.0.1:8766 (LISTEN)

After relaunch:
Mon Oct 19 20:46:56 JST 2026
COMMAND    PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 2919   aa    4u  IPv4 0xaa7e0df50ccb5b4e      0t0  TCP 127.0.0.1:8766 (LISTEN)
 2877     1 /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk
 2919  2877 /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk
http 200
{"desk": {"reachable": true, "url": "http://127.0.0.1:8766"}, "llm": {"status": "idle", "model": null, "loaded_by": null, "active_chats": 0}, "media": {"running": false, "kind": null}, "version": {"cli": "1.0.0", "desk": "1.0.0"}}
