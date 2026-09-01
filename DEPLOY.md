# Deploying `collections` to wbm-studio170

SSH to the studio needs **Tailscale OFF** on the laptop; git.archive.org needs it **ON**.

```sh
# 1. laptop → studio
/Applications/Tailscale.app/Contents/MacOS/Tailscale down
rsync -a --delete --exclude venv --exclude cache --exclude '__pycache__' \
      ~/Documents/collections-explorer/ studio:~/collections-explorer/

# 2. register the service (allocates the port, scaffolds launchd + Caddy + menu entry)
ssh studio 'service new collections --proxy'      # note the port it picks

# 3. move the code into place and build the venv
ssh studio '
  set -e
  sudo rsync -a ~/collections-explorer/ /opt/services/collections/
  sudo chown -R mark:admin /opt/services/collections
  sudo chmod -R g+rwX /opt/services/collections
  mkdir -p /opt/services/collections/logs
  cd /opt/services/collections/app
  /opt/homebrew/bin/python3 -m venv venv
  ./venv/bin/pip -q install flask
  ./venv/bin/python refresh.py            # first harvest, ~3 min
'

# 4. enable + verify
ssh studio 'service enable collections && sleep 3 && curl -s localhost:8331/healthz'
ssh studio 'sudo cp /opt/services/collections/launchd-refresh.plist /Library/LaunchDaemons/ \
            && sudo launchctl bootstrap system /Library/LaunchDaemons/com.wbmstudio.collections-refresh.plist'
curl -sk https://208.70.27.170/collections/healthz

/Applications/Tailscale.app/Contents/MacOS/Tailscale up
```

If `service new` picks a port other than 8331, update it in **three** places:
`run.sh`, `caddy`, `launchd.plist`.

Everything under `/opt/services` is co-owned by the `admin` group (mark + mattb) with an
inherited ACL, so most edits need no sudo — but `service new` creates the tree as whoever
runs it, hence the `chown`/`chmod` above.
